import os
import sys
import re
import json
import math
import time
import base64
import logging
import threading
import subprocess
import urllib.parse
import urllib.request
import requests
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from PIL import Image

logger = logging.getLogger(__name__)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env")
except Exception:
    pass

torch: Any = None
try:
    import torch
except ImportError:
    pass

cv2: Any = None
try:
    import cv2
except ImportError:
    pass


def get_device() -> Any:
    t: Any = torch
    if t is not None and t.cuda.is_available():
        return t.device("cuda")
    elif t is not None:
        return t.device("cpu")
    return "cpu"


def preprocess_clean_internet_image(image_input: Any) -> Image.Image:
    """
    Автоматически детектирует и обрезает однотонные черные/белые полосы (letterboxing),
    рамки скриншотов смартфонов и плашки соцсетей по краям кадра.
    Защищает sky_ratio и эмбеддинги GeoCLIP от искажения однотонными полями.
    """
    if isinstance(image_input, (str, Path)):
        img = Image.open(image_input).convert("RGB")
    elif isinstance(image_input, Image.Image):
        img = image_input.convert("RGB")
    elif np is not None and isinstance(image_input, np.ndarray):
        img = Image.fromarray(cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB) if cv2 is not None else image_input).convert("RGB")
    else:
        return image_input

    w, h = img.size
    if w < 100 or h < 100:
        return img

    arr = np.array(img, dtype=np.uint8)
    gray = (0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]).astype(np.float32)

    def is_solid_border_row(row_idx: int) -> bool:
        row = gray[row_idx, :]
        mean_v = float(np.mean(row))
        std_v = float(np.std(row))
        return (mean_v < 22.0 or mean_v > 238.0) and (std_v < 9.0)

    def is_solid_border_col(col_idx: int) -> bool:
        col = gray[:, col_idx]
        mean_v = float(np.mean(col))
        std_v = float(np.std(col))
        return (mean_v < 22.0 or mean_v > 238.0) and (std_v < 9.0)

    max_h_crop = int(h * 0.25)
    max_w_crop = int(w * 0.25)

    top_crop = 0
    for r in range(max_h_crop):
        if is_solid_border_row(r):
            top_crop = r + 1
        else:
            break

    bottom_crop = h
    for r in range(h - 1, h - 1 - max_h_crop, -1):
        if is_solid_border_row(r):
            bottom_crop = r
        else:
            break

    left_crop = 0
    for c in range(max_w_crop):
        if is_solid_border_col(c):
            left_crop = c + 1
        else:
            break

    right_crop = w
    for c in range(w - 1, w - 1 - max_w_crop, -1):
        if is_solid_border_col(c):
            right_crop = c
        else:
            break

    if (bottom_crop - top_crop) >= int(h * 0.50) and (right_crop - left_crop) >= int(w * 0.50):
        if top_crop > 0 or bottom_crop < h or left_crop > 0 or right_crop < w:
            return img.crop((left_crop, top_crop, right_crop, bottom_crop))

    return img


def compute_image_dhash(img: Image.Image, hash_size: int = 8) -> str:
    """Вычисляет 64-битный разностный хэш (dHash) для мгновенного сопоставления дубликатов."""
    resized = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    arr = np.asarray(resized, dtype=np.int32)
    diff = (arr[:, :-1] > arr[:, 1:]).flatten().tolist()
    decimal_val = 0
    hex_str = []
    for index, value in enumerate(diff):
        if value:
            decimal_val += 2 ** (index % 4)
        if (index % 4) == 3:
            hex_str.append(hex(decimal_val)[2:])
            decimal_val = 0
    return "".join(hex_str)


def extract_multiscale_image_embedding(model_obj: Any, img: Image.Image, device: Any) -> Any:
    """
    5-кропный ансамбль с маскированием центрального объекта на GPU (v2):
    1) Полный очищенный кадр (35%)
    2) Линия горизонта и верхние фасады зданий (15%..70% высоты) (25%)
    3) Левая треть кадра — фон и архитектура слева от объекта (15%)
    4) Правая треть кадра — фон и архитектура справа от объекта (15%)
    5) Центральный кроп (10%)
    Позволяет GeoCLIP видеть архитектуру и биом по краям, даже если в центре кадра селфи или авто.
    """
    if torch is None:
        return None
    w, h = img.size
    crops = [
        img,                                                                     # 1. Полный кадр (35%)
        img.crop((0, int(h * 0.15), w, int(h * 0.70))),                          # 2. Горизонт/фасады (25%)
        img.crop((0, int(h * 0.10), max(1, int(w * 0.38)), int(h * 0.90))),     # 3. Левая треть (15%)
        img.crop((int(w * 0.62), int(h * 0.10), w, int(h * 0.90))),             # 4. Правая треть (15%)
        img.crop((int(w * 0.20), int(h * 0.20), int(w * 0.80), int(h * 0.80)))  # 5. Центральный кроп (10%)
    ]
    weights = torch.tensor([0.35, 0.25, 0.15, 0.15, 0.10], dtype=torch.float32, device=device).unsqueeze(1)

    tensors = [model_obj.image_encoder.preprocess_image(c) for c in crops]
    batch = torch.cat(tensors, dim=0).to(device)

    with torch.no_grad():
        embs = model_obj.image_encoder(batch)
        embs = embs / embs.norm(dim=-1, keepdim=True)
        combined = (embs * weights).sum(dim=0, keepdim=True)
        return combined / combined.norm(dim=-1, keepdim=True)


VISUAL_MEMORY_FILE = ROOT_DIR / "data" / "visual_memory.json"

class LocalVisualMemory:
    """
    Локальная векторная память эталонов (512-d эмбеддинги GeoCLIP + 64-bit dHash).
    При загрузке дубликата, кропа или фото с косинусным сходством > 0.96
    мгновенно возвращает точные координаты с confidence: 0.99.
    """
    def __init__(self, storage_path: Path = VISUAL_MEMORY_FILE):
        self.storage_path = storage_path
        self.entries: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self.load()

    def load(self):
        with self._lock:
            if self.storage_path.exists():
                try:
                    with open(self.storage_path, "r", encoding="utf-8") as f:
                        self.entries = json.load(f)
                except Exception as e:
                    logger.warning("Error loading visual_memory.json: %s", e)
                    self.entries = []
            else:
                self.entries = []

    def save(self):
        with self._lock:
            try:
                self.storage_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.storage_path, "w", encoding="utf-8") as f:
                    json.dump(self.entries[-5000:], f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning("Error saving visual_memory.json: %s", e)

    def find_match(
        self,
        query_emb: Optional[Any],
        query_dhash: Optional[str] = None,
        sim_threshold: float = 0.96,
        region_mode: str = "global"
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            if not self.entries:
                return None

            def _is_region_allowed(entry_lat: float, entry_lon: float) -> bool:
                if region_mode == "kz":
                    return (40.0 <= entry_lat <= 56.0) and (46.0 <= entry_lon <= 88.0)
                return True

            # 1. Проверка dHash (мгновенный поиск дубликатов/кропов)
            if query_dhash:
                try:
                    q_int = int(query_dhash, 16)
                    for entry in reversed(self.entries):
                        if not _is_region_allowed(entry.get("lat", 0.0), entry.get("lon", 0.0)):
                            continue
                        e_hash = entry.get("dhash")
                        if e_hash:
                            h_dist = bin(q_int ^ int(e_hash, 16)).count("1")
                            if h_dist <= 4:
                                return {
                                    "lat": entry["lat"],
                                    "lon": entry["lon"],
                                    "name": entry.get("name", "Exact Visual Duplicate"),
                                    "country": entry.get("country"),
                                    "city": entry.get("city"),
                                    "sim": round(1.0 - (h_dist / 64.0), 4),
                                    "match_type": "dhash_duplicate",
                                    "confidence": 0.99
                                }
                except Exception:
                    pass

            # 2. Проверка косинусного сходства 512-d GeoCLIP эмбеддинга
            if query_emb is not None and len(self.entries) > 0:
                try:
                    if hasattr(query_emb, "cpu"):
                        q_vec = query_emb.cpu().detach().numpy().astype(np.float32).reshape(-1)
                    else:
                        q_vec = np.asarray(query_emb, dtype=np.float32).reshape(-1)
                    q_norm = float(np.linalg.norm(q_vec))
                    if q_norm > 0:
                        q_vec = q_vec / q_norm

                    best_sim = -1.0
                    best_entry = None
                    for entry in reversed(self.entries):
                        if not _is_region_allowed(entry.get("lat", 0.0), entry.get("lon", 0.0)):
                            continue
                        stored_emb = entry.get("embedding")
                        if stored_emb and len(stored_emb) == 512:
                            s_vec = np.asarray(stored_emb, dtype=np.float32)
                            sim = float(np.dot(q_vec, s_vec))
                            if sim > best_sim:
                                best_sim = sim
                                best_entry = entry

                    if best_entry is not None and best_sim >= sim_threshold:
                        return {
                            "lat": best_entry["lat"],
                            "lon": best_entry["lon"],
                            "name": best_entry.get("name", "High-Similarity Visual Match"),
                            "country": best_entry.get("country"),
                            "city": best_entry.get("city"),
                            "sim": round(best_sim, 4),
                            "match_type": "embedding_cosine",
                            "confidence": 0.99
                        }
                except Exception:
                    pass

        return None

    def add_entry(
        self,
        emb_vector: Optional[Any],
        dhash: Optional[str],
        lat: float,
        lon: float,
        name: str = "",
        country: Optional[str] = None,
        city: Optional[str] = None
    ):
        with self._lock:
            emb_list = None
            if emb_vector is not None:
                try:
                    if hasattr(emb_vector, "cpu"):
                        vec = emb_vector.cpu().detach().numpy().astype(np.float32).reshape(-1)
                    else:
                        vec = np.asarray(emb_vector, dtype=np.float32).reshape(-1)
                    norm = float(np.linalg.norm(vec))
                    if norm > 0:
                        vec = vec / norm
                    emb_list = [round(float(x), 5) for x in vec.tolist()[:512]]
                except Exception:
                    pass

            record = {
                "dhash": dhash,
                "embedding": emb_list,
                "lat": float(lat),
                "lon": float(lon),
                "name": name if name else "",
                "country": country,
                "city": city,
                "timestamp": round(time.time(), 2)
            }
            self.entries.append(record)
            if len(self.entries) > 5000:
                self.entries = self.entries[-5000:]
        self.save()

visual_memory = LocalVisualMemory()


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


# Мультиязычные стоп-слова, которые часто встречаются внутри зданий и дают ложные совпадения в OSM (RU, KZ, EN, ES, FR, DE, TR)
INDOOR_OCR_STOPWORDS = {
    # Russian
    "выход", "вход", "касса", "акция", "скидки", "скидка", "этаж", "лифт", "туалет", "wc",
    "гардероб", "зал", "зона", "терминал", "банкомат", "администрация", "информация", "стойка",
    "паркинг", "цоколь", "цокольный", "осторожно", "внимание", "курение", "на себя", "от себя",
    "открыто", "закрыто", "меню", "кофе", "чай",
    # Kazakh
    "шығу", "кіру", "ашық", "жабық", "қабат", "дәретхана", "намазхана", "ақпарат", "жеңілдік",
    "қош", "келдіңіздер",
    # English
    "exit", "entrance", "enter", "welcome", "cashier", "checkout", "floor", "level", "restroom",
    "toilet", "elevator", "stairs", "sale", "discount", "open", "close", "closed", "push", "pull",
    "wifi", "wi-fi", "parking", "p1", "p2", "p3", "information", "info", "warning", "caution",
    "smoking", "no smoking", "coffee", "tea", "menu",
    # Spanish
    "salida", "entrada", "caja", "rebajas", "descuento", "piso", "planta", "baño", "servicios",
    "ascensor", "escaleras", "abierto", "cerrado", "empujar", "tirar", "aparcamiento", "cajero",
    # French
    "sortie", "entrée", "caisse", "solde", "soldes", "étage", "niveau", "toilettes", "ascenseur",
    "escalier", "ouvert", "fermé", "pousser", "tirer", "stationnement",
    # German
    "ausgang", "eingang", "kasse", "rabatt", "etage", "stock", "stockwerk", "aufzug", "treppe",
    "geöffnet", "geschlossen", "drücken", "ziehen", "parkplatz", "parkhaus",
    # Turkish
    "çıkış", "giriş", "kasa", "indirim", "kat", "tuvalet", "asansör", "merdiven", "açık", "kapalı",
    "itiniz", "çekiniz", "otopark", "danışma"
}

# Международные телефонные коды стран
GLOBAL_COUNTRY_PHONE_CODES = {
    "+1": ("United States / Canada", "US", 39.8283, -98.5795),
    "+44": ("United Kingdom", "GB", 55.3781, -3.4360),
    "+49": ("Germany", "DE", 51.1657, 10.4515),
    "+33": ("France", "FR", 46.2276, 2.2137),
    "+81": ("Japan", "JP", 36.2048, 138.2529),
    "+82": ("South Korea", "KR", 35.9078, 127.7669),
    "+86": ("China", "CN", 35.8617, 104.1954),
    "+90": ("Turkey", "TR", 38.9637, 35.2433),
    "+971": ("United Arab Emirates", "AE", 23.4241, 53.8478),
    "+39": ("Italy", "IT", 41.8719, 12.5674),
    "+34": ("Spain", "ES", 40.4637, -3.7492),
    "+48": ("Poland", "PL", 51.9194, 19.1451),
    "+31": ("Netherlands", "NL", 52.1326, 5.2913),
    "+41": ("Switzerland", "CH", 46.8182, 8.2275),
    "+43": ("Austria", "AT", 47.5162, 14.5501),
    "+46": ("Sweden", "SE", 60.1282, 18.6435),
    "+47": ("Norway", "NO", 60.4720, 8.4689),
    "+358": ("Finland", "FI", 61.9241, 25.7482),
    "+61": ("Australia", "AU", -25.2744, 133.7751),
    "+55": ("Brazil", "BR", -14.2350, -51.9253),
    "+91": ("India", "IN", 20.5937, 78.9629),
    "+65": ("Singapore", "SG", 1.3521, 103.8198),
    "+966": ("Saudi Arabia", "SA", 23.8859, 45.0792),
    "+996": ("Kyrgyzstan", "KG", 41.2044, 74.7661),
    "+998": ("Uzbekistan", "UZ", 41.3775, 64.5853),
    "+994": ("Azerbaijan", "AZ", 40.1431, 47.5769),
    "+995": ("Georgia", "GE", 42.3154, 43.3569),
}

# Национальные доменные зоны стран (ccTLDs)
GLOBAL_CCTLDS = {
    ".us": ("United States", "US", 39.8283, -98.5795),
    ".uk": ("United Kingdom", "GB", 55.3781, -3.4360),
    ".co.uk": ("United Kingdom", "GB", 55.3781, -3.4360),
    ".de": ("Germany", "DE", 51.1657, 10.4515),
    ".fr": ("France", "FR", 46.2276, 2.2137),
    ".jp": ("Japan", "JP", 36.2048, 138.2529),
    ".kr": ("South Korea", "KR", 35.9078, 127.7669),
    ".cn": ("China", "CN", 35.8617, 104.1954),
    ".tr": ("Turkey", "TR", 38.9637, 35.2433),
    ".ae": ("United Arab Emirates", "AE", 23.4241, 53.8478),
    ".it": ("Italy", "IT", 41.8719, 12.5674),
    ".es": ("Spain", "ES", 40.4637, -3.7492),
    ".pl": ("Poland", "PL", 51.9194, 19.1451),
    ".nl": ("Netherlands", "NL", 52.1326, 5.2913),
    ".ch": ("Switzerland", "CH", 46.8182, 8.2275),
    ".at": ("Austria", "AT", 47.5162, 14.5501),
    ".se": ("Sweden", "SE", 60.1282, 18.6435),
    ".no": ("Norway", "NO", 60.4720, 8.4689),
    ".fi": ("Finland", "FI", 61.9241, 25.7482),
    ".au": ("Australia", "AU", -25.2744, 133.7751),
    ".br": ("Brazil", "BR", -14.2350, -51.9253),
    ".ca": ("Canada", "CA", 56.1304, -106.3468),
    ".in": ("India", "IN", 20.5937, 78.9629),
    ".sg": ("Singapore", "SG", 1.3521, 103.8198),
    ".kz": ("Kazakhstan", "KZ", 48.0196, 66.9237),
    ".ru": ("Russia", "RU", 61.5240, 105.3188),
    ".ua": ("Ukraine", "UA", 48.3794, 31.1656),
    ".ge": ("Georgia", "GE", 42.3154, 43.3569),
    ".uz": ("Uzbekistan", "UZ", 41.3775, 64.5853),
    ".kg": ("Kyrgyzstan", "KG", 41.2044, 74.7661),
    ".az": ("Azerbaijan", "AZ", 40.1431, 47.5769),
}

# Мировые символы валют
GLOBAL_CURRENCIES = {
    "€": ("Eurozone", "EU", 50.0, 10.0),
    "£": ("United Kingdom", "GB", 55.3781, -3.4360),
    "$": ("United States / Americas", "US", 39.8283, -98.5795),
    "¥": ("Japan / China", "JP", 36.2048, 138.2529),
    "₩": ("South Korea", "KR", 35.9078, 127.7669),
    "₺": ("Turkey", "TR", 38.9637, 35.2433),
    "₹": ("India", "IN", 20.5937, 78.9629),
    "₸": ("Kazakhstan", "KZ", 48.0196, 66.9237),
    "₽": ("Russia", "RU", 61.5240, 105.3188),
    "CHF": ("Switzerland", "CH", 46.8182, 8.2275),
    "AED": ("United Arab Emirates", "AE", 23.4241, 53.8478),
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
    ("Burabay (Borovoe), Zhumbaktas & Okzhetpes", 53.0837, 70.2709, 6000, 200),
    # 2. Алматы и знаковые локации
    ("Almaty City & Arbat", 43.2389, 76.8897, 12000, 300),
    ("Almaty, First President Park", 43.1903, 76.8858, 3000, 150),
    ("Almaty, Central Park (Gorky Park)", 43.2625, 76.9686, 2500, 150),
    ("Almaty, Botanical Garden", 43.2197, 76.9136, 2000, 150),
    ("Almaty, Kok-Tobe & Terrenkur", 43.2330, 76.9760, 4000, 200),
    ("Almaty, Panfilov Park & Zenkov Cathedral", 43.2588, 76.9535, 2500, 150),
    ("Almaty, Medeu High-Altitude Skating Rink", 43.1575, 77.0589, 5000, 200),
    ("Almaty, Shymbulak Ski Resort", 43.1284, 77.0811, 4000, 200),
    ("Almaty, Big Almaty Lake (BAO)", 43.0506, 76.9850, 4000, 200),
    # 3. Природные жемчужины Алматинского региона
    ("Kolsai Lakes National Park", 42.9897, 78.3256, 5000, 200),
    ("Kaindy Lake (Sunken Forest)", 42.9844, 78.4660, 4000, 200),
    ("Charyn Canyon (Valley of Castles)", 43.3550, 79.0792, 6000, 200),
    # 4. Астана (Левый берег, Байтерек, Мечеть, Ботанический)
    ("Astana, Baiterek, Central Park & Botanical Garden", 51.1280, 71.4300, 12000, 300),
    ("Astana, Grand Mosque & Expo", 51.0729, 71.4096, 10000, 250),
    # 5. Другие крупные города РК
    ("Karaganda, Central Park & City", 49.8047, 73.1094, 10000, 300),
    ("Shymkent, Parks & City", 42.3417, 69.5901, 10000, 300),
    ("Turkestan, Khoja Ahmed Yasawi Mausoleum", 43.2973, 68.2517, 6000, 200),
    ("Aktau & Caspian Sea Coast", 43.6532, 51.1691, 10000, 300),
    ("Mangystau, Bozzhira Tract (Ustyurt)", 43.4167, 54.0667, 6000, 200),
    ("Ust-Kamenogorsk & Altai Foothills", 49.9483, 82.6285, 8000, 300),
    ("East Kazakhstan, Katon-Karagay & Belukha", 49.1667, 85.6000, 8000, 250),
    ("Aktobe", 50.2839, 57.1670, 8000, 300),
    ("Taraz", 42.9000, 71.3667, 8000, 300),
    ("Pavlodar", 52.2873, 76.9674, 8000, 300),
    ("Semey", 50.4111, 80.2275, 8000, 300),
    ("Atyrau", 47.0945, 51.9238, 8000, 300),
    ("Kokshetau", 53.2833, 69.3833, 8000, 300),
    ("Kostanay", 53.2144, 63.6246, 8000, 300),
    ("Kyzylorda", 44.8488, 65.4823, 8000, 300),
    ("Uralsk", 51.2333, 51.3667, 8000, 300),
    ("Petropavlovsk", 54.8728, 69.1430, 8000, 300),
    ("Taldykorgan", 45.0156, 78.3739, 8000, 300),
]

# Ключевые мировые мега-хабы и знаковые архитектурные локации
WORLD_HUBS = [
    ("Paris, Eiffel Tower & Champs-Elysees", 48.8584, 2.2945, 10000, 300),
    ("London, Big Ben & Westminster", 51.5007, -0.1246, 10000, 300),
    ("Tokyo, Shibuya & Tokyo Tower", 35.6586, 139.7454, 12000, 300),
    ("New York, Manhattan & Times Square", 40.7580, -73.9855, 12000, 300),
    ("Rome, Colosseum & Vatican", 41.8902, 12.4922, 9000, 300),
    ("Istanbul, Sultanahmet & Bosphorus", 41.0082, 28.9784, 12000, 300),
    ("Dubai, Downtown & Burj Khalifa", 25.1972, 55.2744, 10000, 300),
    ("Berlin, Brandenburg Gate & Mitte", 52.5163, 13.3777, 10000, 300),
    ("Sydney, Opera House & Harbor", -33.8568, 151.2153, 10000, 300),
    ("Singapore, Marina Bay Sands", 1.2838, 103.8591, 8000, 300),
    ("Cairo, Giza Pyramids & Nile", 29.9792, 31.1342, 10000, 300),
    ("Seoul, Gangnam & N Seoul Tower", 37.5512, 126.9882, 12000, 300),
    ("Rio de Janeiro, Christ the Redeemer", -22.9519, -43.2105, 10000, 300),
    ("San Francisco, Golden Gate & Bay Area", 37.7749, -122.4194, 10000, 300),
    ("Hong Kong, Victoria Peak & Central", 22.2800, 114.1588, 8000, 300),
    ("Bangkok, Grand Palace & Chao Phraya", 13.7500, 100.5000, 10000, 300),
    ("Amsterdam, Canals & Center", 52.3676, 4.9041, 8000, 300),
    ("Madrid, Puerta del Sol & Gran Via", 40.4168, -3.7038, 10000, 300),
    ("Vienna, Historic Center", 48.2082, 16.3738, 8000, 300),
    ("Prague, Charles Bridge & Old Town", 50.0875, 14.4211, 8000, 300),
    ("Barcelona, Sagrada Familia & Beach", 41.4036, 2.1744, 8000, 300),
    ("Toronto, CN Tower & Downtown", 43.6426, -79.3871, 10000, 300),
    ("Beijing, Forbidden City", 39.9042, 116.4074, 12000, 300),
    ("Buenos Aires, Obelisco", -34.6037, -58.3816, 10000, 300),
    ("Tashkent, Amir Timur Square", 41.3111, 69.2797, 10000, 300),
    ("Bishkek, Ala-Too Square", 42.8746, 74.6122, 8000, 300),
    ("Baku, Flame Towers & Boulevard", 40.3756, 49.8328, 8000, 300),
    ("Tbilisi, Old Town & Narikala", 41.6938, 44.8015, 8000, 300),
]


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


def enrich_geoclip_gallery(geoclip_model, region_mode: str = "global"):
    """
    Обогащает галерею GeoCLIP:
    1. По умолчанию (region_mode="global") сохраняет полную мировую галерею GeoCLIP (~100 000 точек)
       и добавляет к ней плотную сетку хабов Казахстана и ключевых мировых локаций.
    2. При region_mode="kz" переключает модель на локальную сетку Казахстана.
    """
    if torch is None:
        return
    model_obj = _unwrap_geoclip(geoclip_model)
    if model_obj is None or not hasattr(model_obj, "gps_gallery"):
        return

    # Сохраняем исходную глобальную галерею GeoCLIP (100k мировых точек)
    if not hasattr(model_obj, "_original_global_gallery"):
        model_obj._original_global_gallery = model_obj.gps_gallery.clone()

    if not hasattr(model_obj, "_global_gallery") or not hasattr(model_obj, "_kz_gallery"):
        try:
            device = model_obj.gps_gallery.device
            grids_kz = [_build_grid(lat, lon, r, s) for (_, lat, lon, r, s) in KZ_HUBS]
            grids_world = [_build_grid(lat, lon, r, s) for (_, lat, lon, r, s) in WORLD_HUBS]
            kz_arr = np.vstack(grids_kz)
            world_extra_arr = np.vstack(grids_world) if grids_world else np.empty((0, 2), dtype=np.float32)

            kz_tensor = torch.tensor(kz_arr, dtype=torch.float32, device=device)
            extra_tensor = torch.tensor(np.vstack([kz_arr, world_extra_arr]), dtype=torch.float32, device=device)

            model_obj._kz_gallery = kz_tensor
            model_obj._global_gallery = torch.cat([model_obj._original_global_gallery, extra_tensor], dim=0)
        except Exception as e:
            logger.warning("Error building enriched galleries: %s", e)
            model_obj._global_gallery = model_obj._original_global_gallery

    # Применяем режим
    if region_mode == "kz" and hasattr(model_obj, "_kz_gallery"):
        model_obj.gps_gallery = model_obj._kz_gallery
    else:
        model_obj.gps_gallery = getattr(model_obj, "_global_gallery", model_obj._original_global_gallery)


def set_geoclip_region(geoclip_model, region_mode: str = "global"):
    """Переключает активную сетку GeoCLIP между 'global' и 'kz'."""
    enrich_geoclip_gallery(geoclip_model, region_mode=region_mode)


def lock_geoclip_to_kazakhstan(geoclip_model):
    """Принудительно устанавливает фокус галереи на Казахстан (обратная совместимость)."""
    enrich_geoclip_gallery(geoclip_model, region_mode="kz")



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
            combined_sky = cv2.bitwise_or(sky_mask_blue, sky_mask_bright)
            sky_ratio = float(np.count_nonzero(combined_sky)) / float(top_crop.shape[0] * top_crop.shape[1])

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


def extract_global_and_kz_clues(texts: List[Any]) -> Dict[str, Any]:
    """
    Универсальный парсер микро-признаков по всему миру и Казахстану:
    1. Казахстанские правила (почтовые индексы, городские коды телефонов, автономера 01-20, БИН).
    2. Глобальные правила (международные телефонные коды стран +1..+998, национальные доменные зоны, символы валют).
    """
    matched_clues: List[str] = []
    clues: Dict[str, Any] = {
        "country": None,
        "country_code": None,
        "postal_code": None,
        "phone_code": None,
        "plate_region": None,
        "bin": None,
        "inferred_city": None,
        "anchor_lat": None,
        "anchor_lon": None,
        "confidence": 0.0,
        "matched_clues": matched_clues
    }
    if not texts:
        return clues

    joined = " ".join([str(t) for t in texts if t is not None])

    # 1. Казахстан: Почтовые индексы (старый 6-значный 010000..169999)
    m_post_old = re.search(r"\b(0[1-9]|1[0-6])\d{4}\b", joined)
    if m_post_old:
        code = m_post_old.group(0)
        prefix = code[:2]
        if prefix in KZ_POSTAL_PREFIXES:
            city_name, lat, lon = KZ_POSTAL_PREFIXES[prefix]
            clues["country"] = "Kazakhstan"
            clues["country_code"] = "KZ"
            clues["postal_code"] = code
            clues["inferred_city"] = city_name
            clues["anchor_lat"] = lat
            clues["anchor_lon"] = lon
            clues["confidence"] = 0.90
            matched_clues.append(f"KZ Postal Code {code} -> {city_name}")

    # Казахстан: Новый 7-значный индекс Казпочты (например, A05B2Y3)
    if not clues["postal_code"]:
        m_post_new = re.search(r"\b([A-Z])\d{2}[A-Z0-9]{4}\b", joined)
        if m_post_new:
            code = m_post_new.group(0)
            first_letter = code[0]
            if first_letter in KAZPOST_NEW_LETTERS:
                city_name, lat, lon = KAZPOST_NEW_LETTERS[first_letter]
                clues["country"] = "Kazakhstan"
                clues["country_code"] = "KZ"
                clues["postal_code"] = code
                clues["inferred_city"] = city_name
                clues["anchor_lat"] = lat
                clues["anchor_lon"] = lon
                clues["confidence"] = 0.88
                matched_clues.append(f"Kazpost {code} -> {city_name}")

    # 2. Казахстан: Телефонные коды городов (+7 727, (7172), 8(7252))
    for code, (city_name, lat, lon) in KZ_PHONE_CODES.items():
        pattern = rf"(?:\+7|8)[\s\-\(]*{code}[\s\-\)]*\d+"
        if re.search(pattern, joined):
            clues["phone_code"] = code
            if not clues["inferred_city"]:
                clues["country"] = "Kazakhstan"
                clues["country_code"] = "KZ"
                clues["inferred_city"] = city_name
                clues["anchor_lat"] = lat
                clues["anchor_lon"] = lon
                clues["confidence"] = 0.85
            matched_clues.append(f"KZ Phone Code {code} -> {city_name}")
            break

    # 3. Казахстан: Автомобильные номера РК (123 ABC 02 или 02 | 123 ABC)
    plate_match = re.search(r"\b\d{3}\s?[A-Z]{2,3}\s?(0[1-9]|1[0-9]|20)\b", joined) or \
                  re.search(r"\b(0[1-9]|1[0-9]|20)\s?\|\s?\d{3}\s?[A-Z]{2,3}\b", joined)
    if plate_match:
        reg = plate_match.group(1)
        if reg in KZ_PLATE_REGIONS:
            city_name, lat, lon = KZ_PLATE_REGIONS[reg]
            clues["plate_region"] = reg
            if not clues["inferred_city"]:
                clues["country"] = "Kazakhstan"
                clues["country_code"] = "KZ"
                clues["inferred_city"] = city_name
                clues["anchor_lat"] = lat
                clues["anchor_lon"] = lon
                clues["confidence"] = 0.80
            matched_clues.append(f"KZ License Plate Region {reg} -> {city_name}")

    # 4. Казахстан: БИН / ИИН (12 цифр)
    bin_match = re.search(r"\b(БИН|ИИН|BIN|IIN)[:\s]*([0-9]{12})\b", joined, re.IGNORECASE)
    if bin_match:
        clues["bin"] = bin_match.group(2)
        matched_clues.append(f"Kazakh Fiscal BIN: {clues['bin']}")

    # 5. МЕЖДУНАРОДНЫЕ ТЕЛЕФОННЫЕ КОДЫ СТРАН (если страна ещё не зафиксирована с высокой уверенностью)
    conf_val = float(clues.get("confidence") or 0.0)
    if not clues["country_code"] or conf_val < 0.85:
        for p_code, (c_name, c_iso, c_lat, c_lon) in GLOBAL_COUNTRY_PHONE_CODES.items():
            esc = re.escape(p_code)
            pattern = rf"(?:^|[^\d])({esc})[\s\-\(]*\d{{2,4}}[\s\-\)]*\d+"
            if re.search(pattern, joined):
                clues["country"] = c_name
                clues["country_code"] = c_iso
                clues["phone_code"] = p_code
                if not clues["anchor_lat"]:
                    clues["anchor_lat"] = c_lat
                    clues["anchor_lon"] = c_lon
                    clues["confidence"] = 0.78
                matched_clues.append(f"International Phone Prefix {p_code} -> {c_name} ({c_iso})")
                break

    # 6. НАЦИОНАЛЬНЫЕ ДОМЕННЫЕ ЗОНЫ (ccTLDs) НА БАННЕРАХ / ВЫВЕСКАХ (.de, .fr, .jp, .uk, .tr, .kz...)
    for tld, (c_name, c_iso, c_lat, c_lon) in GLOBAL_CCTLDS.items():
        pattern = rf"(?i)\b[a-z0-9\-\.]{{2,}}{re.escape(tld)}(?:[/\s\?]|$)"
        if re.search(pattern, joined):
            if not clues["country_code"]:
                clues["country"] = c_name
                clues["country_code"] = c_iso
                if not clues["anchor_lat"]:
                    clues["anchor_lat"] = c_lat
                    clues["anchor_lon"] = c_lon
                    clues["confidence"] = 0.75
            matched_clues.append(f"ccTLD {tld} -> {c_name} ({c_iso})")
            break

    # 7. МИРОВЫЕ ВАЛЮТЫ (€, £, $, ¥, ₩, ₺, ₸, ₽, AED, CHF)
    for curr_sym, (c_name, c_iso, c_lat, c_lon) in GLOBAL_CURRENCIES.items():
        pattern = rf"(?:^|[^\w]){re.escape(curr_sym)}(?:[\s\d]|$)|(?:\d+[\s]*{re.escape(curr_sym)})"
        if re.search(pattern, joined):
            if not clues["country_code"]:
                clues["country"] = c_name
                clues["country_code"] = c_iso
                if not clues["anchor_lat"]:
                    clues["anchor_lat"] = c_lat
                    clues["anchor_lon"] = c_lon
                    clues["confidence"] = 0.65
            matched_clues.append(f"Currency Symbol {curr_sym} -> {c_name} ({c_iso})")
            break

    return clues


def extract_kz_metadata_clues(texts: List[str]) -> Dict[str, Any]:
    """Алиас для обратной совместимости."""
    return extract_global_and_kz_clues(texts)



def search_overpass_brand_cluster(
    brands: List[Any],
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
            "You are a world-class OSINT geolocator and professional GeoGuessr champion specializing in worldwide visual geolocation across all continents (Europe, Asia, Americas, Middle East, Africa, Oceania, CIS & Kazakhstan).\n"
            "Analyze the image and extract key geographical, infrastructural, natural, and linguistic signatures:\n\n"
            "1. SCENE CONTEXT & ENVIRONMENT:\n"
            "- Determine if the photo is taken INDOORS (inside a building, mall, cafe, office, room, station, airport) or OUTDOORS (street, highway, park, nature, mountains, coast, architectural facade).\n"
            "- If INDOORS: identify recognizable mall atrium architecture (MEGA, Dostyk Plaza, Khan Shatyr, Westfield, Galeries Lafayette, Dubai Mall, etc.), storefront names, airport terminal designs, signs, brands.\n"
            "- If WINDOW/BALCONY: inspect outside landmarks (mountains, towers, skylines, water bodies).\n"
            "- DO NOT guess random coordinates if indoor room is generic/unidentifiable — set lat and lon to null if confidence is below 0.65.\n\n"
            "2. GLOBAL GEOGUESSR & ROAD/INFRASTRUCTURE SIGNATURES (CRITICAL):\n"
            "- Driving side: Left-Hand Traffic (LHT: UK, Japan, Australia, New Zealand, South Africa, India, Thailand, Indonesia, Malaysia, etc.) vs Right-Hand Traffic (RHT: Europe, Americas, CIS/Kazakhstan, China, etc.).\n"
            "- Road markings: white vs yellow dashed/solid center lines, outer shoulder lines, chevron arrows.\n"
            "- Road bollards and reflectors: shape, colors (e.g. red/white, black/white, circular vs rectangular reflectors).\n"
            "- Utility poles: concrete ladder/hole poles (France, Poland, Hungary, Romania), wooden poles, metal lattice, A-frames, step bolts, transformer shapes.\n"
            "- Architecture & Roofing: European terracotta/slate tiles, American siding/shingles, Japanese kawara tiles, Soviet panel housing, Middle Eastern flat rooftops, tropical wooden stilts.\n"
            "- Flora & Biome: pine/birch boreal forest, Mediterranean olive/cypress, tropical palm/eucalyptus, dry steppe/desert, tropical red soil vs dark chernozem.\n"
            "- Language, scripts & country-code TLDs on banners/ads: Latin, Cyrillic, Greek, Arabic, Kanji/Kana (Japan), Hangul (Korea), Hanzi (China), Thai, Devanagari, Hebrew. Look for domain zones (.de, .fr, .jp, .uk, .tr, .ae, .us, .ca, .br, .au, .it, .es, .pl, .kz, .ru, etc.) and currencies ($, €, £, ¥, ₩, ₺, ₹, ₸, ₽, AED, CHF).\n"
            "- Vehicle plates: EU blue strip, UK/NL yellow rear plates, long white plates, square Japanese/US plates, Kazakh 01-20 plate style.\n\n"
            "3. TERRAIN BEARING & MOUNTAIN ORIENTATION:\n"
            "- If mountains, coastline, lake, or major river are visible:\n"
            "  * 'terrain_bearing': {'feature': 'mountains|sea|river|lake', 'direction': 'Looking South towards Alps / Coastline / Mountain Ridge', 'notes': 'perspective description'}.\n"
            "- If in ALMATY or near Zailiyskiy Alatau:\n"
            "  * 'almaty_mountain_bearing': visibility of ridge or Kok-Tobe, shooting angle, city sector ('Верхняя часть / Медеу', 'Центр', 'Нижняя часть').\n\n"
            "Return ONLY valid JSON matching this schema:\n"
            "{\n"
            '  "is_indoor": true/false,\n'
            '  "scene_type": "mall|cafe|office|residential|station|airport|street|highway|park|nature|coast",\n'
            '  "country": "Country name (e.g. France, Japan, Turkey, Kazakhstan, United States)",\n'
            '  "country_code": "ISO-2 code (e.g. FR, JP, TR, KZ, US, GB, DE)",\n'
            '  "city": "City or region name or null",\n'
            '  "place_name": "exact landmark name or null",\n'
            '  "confidence": 0.85,\n'
            '  "lat": 48.8584_or_null,\n'
            '  "lon": 2.2945_or_null,\n'
            '  "radius_m": 30,\n'
            '  "driving_side": "RHT" or "LHT",\n'
            '  "osm_search_query": "search query for OpenStreetMap",\n'
            '  "search_queries": ["identifiable brand, mall, landmark, road or window view"],\n'
            '  "detected_text": ["visible text"],\n'
            '  "terrain_bearing": {\n'
            '    "feature": "mountains|sea|river|lake|none",\n'
            '    "direction": "direction description",\n'
            '    "notes": "perspective description"\n'
            '  },\n'
            '  "almaty_mountain_bearing": {\n'
            '    "mountain_visible": true/false,\n'
            '    "kok_tobe_visible": true/false,\n'
            '    "shooting_angle": "Looking South toward Zailiyskiy Alatau",\n'
            '    "city_sector": "Верхняя часть / Медеу|Центр|Нижняя часть|null",\n'
            '    "sector_lat": 43.215_or_null,\n'
            '    "sector_lon": 76.945_or_null,\n'
            '    "notes": "description"\n'
            '  },\n'
            '  "window_view": {\n'
            '    "has_window_view": true/false,\n'
            '    "window_landmarks": ["landmark name"],\n'
            '    "azimuth_deg": 180,\n'
            '    "notes": "description"\n'
            '  }\n'
            "}"
        )
        payload_with_search = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64}}
                ]
            }],
            "tools": [{"google_search": {}}],
            "generationConfig": {"temperature": 0.1, "response_mime_type": "application/json"}
        }
        payload_standard = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64}}
                ]
            }],
            "generationConfig": {"temperature": 0.1, "response_mime_type": "application/json"}
        }

        models_to_try = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.5-flash-lite"]
        last_err = ""

        for model_name in models_to_try:
            endpoints = [
                (f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}", {}),
                (f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent", {"x-goog-api-key": api_key}),
            ]
            for url, headers in endpoints:
                for payload in [payload_with_search, payload_standard]:
                    try:
                        r = requests.post(url, json=payload, headers=headers, timeout=12)

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


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Вычисляет расстояние в километрах между двумя географическими координатами (WGS84)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(dlam / 2.0) ** 2)
    return 6371.0 * (2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a)))


def verify_and_geocode_landmark(
    name: Optional[str],
    city: Optional[str] = None,
    country: Optional[str] = None,
    llm_lat: Optional[float] = None,
    llm_lon: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """
    1. GOOGLE SEARCH GROUNDING + FORWARD GEOCODING VERIFICATION (Защита от галлюцинации цифр у LLM):
    Проверяет название объекта/ориентира/отеля/ЖК через 3 независимых источника:
    a) Wikipedia Geosearch (en.wikipedia.org и ru.wikipedia.org) — точнейшие координаты мировых и региональных достопримечательностей;
    b) Photon Komoot API (https://photon.komoot.io) — нечеткий поиск POI;
    c) OSM Nominatim API (https://nominatim.openstreetmap.org/search) — точный картографический поиск.
    Если геокодер нашел объект, заменяет сырые числа LLM на точные координаты с radius_m: 20.
    """
    if not name or name.strip().lower() in ("null", "none", "unknown", ""):
        return None

    clean_name = re.sub(r'[\(\)\[\]«»"\'\?!\*]', ' ', name).strip()
    words = clean_name.split()
    if not words or (len(words) == 1 and len(words[0]) < 3):
        return None

    low_single = clean_name.lower()
    if low_single in ("building", "street", "road", "city", "house", "hotel", "cafe", "restaurant", "mall", "park", "здание", "улица", "город", "отель", "кафе"):
        return None

    c_name = city.strip() if city and city.lower() not in ("null", "none", "unknown") else ""
    co_name = country.strip() if country and country.lower() not in ("null", "none", "unknown") else ""

    queries = []
    if c_name and co_name:
        queries.append(f"{clean_name}, {c_name}, {co_name}")
    if c_name:
        queries.append(f"{clean_name}, {c_name}")
    queries.append(clean_name)

    headers = {"User-Agent": "GeoSleuthGlobalResearch/3.5 (LandmarkVerifier)"}

    # a) Wikipedia Search + Coordinates (ru & en)
    for wiki_lang in ("ru", "en"):
        for q in queries:
            try:
                s_url = f"https://{wiki_lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q)}&format=json&utf8=1"
                r = requests.get(s_url, headers=headers, timeout=4)
                if r.ok:
                    items = r.json().get("query", {}).get("search", [])
                    if items:
                        page_title = items[0].get("title")
                        if page_title:
                            c_url = f"https://{wiki_lang}.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote(page_title)}&prop=coordinates&format=json&utf8=1"
                            cr = requests.get(c_url, headers=headers, timeout=4)
                            if cr.ok:
                                pages = cr.json().get("query", {}).get("pages", {})
                                for p in pages.values():
                                    coords = p.get("coordinates")
                                    if coords and len(coords) > 0:
                                        w_lat = float(coords[0]["lat"])
                                        w_lon = float(coords[0]["lon"])
                                        if llm_lat is not None and llm_lon is not None:
                                            d_km = haversine_km(llm_lat, llm_lon, w_lat, w_lon)
                                            if d_km > 150.0 and (not c_name or c_name.lower() not in page_title.lower()):
                                                continue
                                        return {
                                            "verified": True,
                                            "lat": w_lat,
                                            "lon": w_lon,
                                            "name": page_title,
                                            "source": f"Wikipedia ({wiki_lang.upper()})",
                                            "radius_m": 20,
                                            "confidence": 0.98,
                                            "method": f"Verified Landmark Geocode (Wikipedia): {page_title}"
                                        }
            except Exception:
                pass

    # b) Photon Komoot API (быстрый нечеткий поиск)
    for q in queries:
        try:
            p_url = f"https://photon.komoot.io/api/?q={urllib.parse.quote(q)}&limit=3"
            if llm_lat is not None and llm_lon is not None:
                p_url += f"&lat={llm_lat}&lon={llm_lon}"
            r = requests.get(p_url, headers=headers, timeout=4)
            if r.ok:
                features = r.json().get("features", [])
                for f in features:
                    coords = f.get("geometry", {}).get("coordinates", [])
                    if len(coords) >= 2:
                        p_lon = float(coords[0])
                        p_lat = float(coords[1])
                        props = f.get("properties", {})
                        p_name = props.get("name") or q
                        if llm_lat is not None and llm_lon is not None:
                            d_km = haversine_km(llm_lat, llm_lon, p_lat, p_lon)
                            if d_km > 75.0 and (not c_name or c_name.lower() not in (props.get("city") or "").lower()):
                                continue
                        return {
                            "verified": True,
                            "lat": p_lat,
                            "lon": p_lon,
                            "name": p_name,
                            "source": "Photon",
                            "radius_m": 20,
                            "confidence": 0.95,
                            "method": f"Verified Landmark Geocode (Photon): {p_name}"
                        }
        except Exception:
            pass

    # c) OSM Nominatim API (точный поиск)
    for q in queries:
        try:
            nom_params = {
                "q": q,
                "format": "jsonv2",
                "limit": 2,
                "addressdetails": 1
            }
            if llm_lat is not None and llm_lon is not None:
                deg = 35.0 / 111.32
                nom_params["viewbox"] = f"{llm_lon - deg},{llm_lat + deg},{llm_lon + deg},{llm_lat - deg}"
                nom_params["bounded"] = 0

            r = requests.get("https://nominatim.openstreetmap.org/search", params=nom_params, headers=headers, timeout=5)
            if r.ok and r.json():
                hit = r.json()[0]
                n_lat = float(hit["lat"])
                n_lon = float(hit["lon"])
                n_name = hit.get("display_name", q)
                if llm_lat is not None and llm_lon is not None:
                    d_km = haversine_km(llm_lat, llm_lon, n_lat, n_lon)
                    if d_km > 75.0 and (not c_name or c_name.lower() not in n_name.lower()):
                        continue
                return {
                    "verified": True,
                    "lat": n_lat,
                    "lon": n_lon,
                    "name": n_name,
                    "source": "Nominatim",
                    "radius_m": 20,
                    "confidence": 0.95,
                    "method": f"Verified Landmark Geocode (Nominatim): {clean_name}"
                }
        except Exception:
            pass

    return None


def semantic_sanity_check(
    candidate_lat: float,
    candidate_lon: float,
    vlm_data: Dict[str, Any],
    clues: Dict[str, Any],
    verified_landmark: Optional[Dict[str, Any]] = None,
    anchor_lat: Optional[float] = None,
    anchor_lon: Optional[float] = None,
    method_name: str = ""
) -> Tuple[float, float, str, Optional[str]]:
    """
    5. АГЕНТ-КРИТИК: СЕМАНТИЧЕСКАЯ САМОПРОВЕРКА ТОЧКИ:
    - Проверка 1: Если между уверенным ответом Gemini (conf >= 0.75) / проверенным ориентиром
      и точкой GeoCLIP расхождение > 25 км — приоритет отдается связке VLM + Геокодер.
    - Проверка 2: Если Gemini определила сцену как море/пляж/реку, а в радиусе 1.2 км от найденной
      точки GeoCLIP нет воды — понижает вес GeoCLIP и использует координаты проверенного якоря.
    """
    final_lat = candidate_lat
    final_lon = candidate_lon
    final_method = method_name
    sanity_warning = None

    gold_lat = None
    gold_lon = None
    gold_source = None

    if verified_landmark and verified_landmark.get("lat") and verified_landmark.get("lon"):
        gold_lat = float(verified_landmark["lat"])
        gold_lon = float(verified_landmark["lon"])
        gold_source = verified_landmark.get("source", "Verified Landmark")
    elif vlm_data.get("lat") and vlm_data.get("lon") and float(vlm_data.get("confidence") or 0) >= 0.75:
        gold_lat = float(vlm_data["lat"])
        gold_lon = float(vlm_data["lon"])
        gold_source = "Gemini Vision (High Confidence)"
    elif anchor_lat is not None and anchor_lon is not None and float(clues.get("confidence") or 0) >= 0.85:
        gold_lat = float(anchor_lat)
        gold_lon = float(anchor_lon)
        gold_source = "Regional/Postal Anchor"

    # Проверка 1: Расхождение более 25 км
    if gold_lat is not None and gold_lon is not None:
        drift_km = haversine_km(gold_lat, gold_lon, candidate_lat, candidate_lon)
        if drift_km > 25.0:
            final_lat = gold_lat
            final_lon = gold_lon
            final_method = f"Agent-Critic Override ({gold_source}): Drift {drift_km:.1f}km > 25km corrected"
            sanity_warning = f"GeoCLIP grid drifted {drift_km:.1f} km from confirmed semantic landmark; overridden to {gold_source}."
            return final_lat, final_lon, final_method, sanity_warning

    # Проверка 2: Защита гидрографии (море, пляж, река)
    scene = str(vlm_data.get("scene_type", "")).lower()
    t_feat = str(vlm_data.get("terrain_bearing", {}).get("feature", "")).lower()
    is_water_scene = any(w in scene or w in t_feat for w in ("coast", "beach", "sea", "water", "river", "lake", "пляж", "море", "река", "озеро"))

    if is_water_scene and gold_lat is not None and gold_lon is not None:
        try:
            ovp_url = "https://overpass-api.de/api/interpreter"
            q_ovp = f"""[out:json][timeout:3];(way["natural"~"water|coastline|beach"](around:1200,{candidate_lat},{candidate_lon});node["natural"~"water|beach"](around:1200,{candidate_lat},{candidate_lon}););out count;"""
            r = requests.post(ovp_url, data={"data": q_ovp}, timeout=4)
            if r.ok:
                count_elem = r.json().get("elements", [{}])[0].get("tags", {}).get("total", "0")
                if int(count_elem) == 0:
                    final_lat = gold_lat
                    final_lon = gold_lon
                    final_method = f"Agent-Critic Water Guard ({gold_source})"
                    sanity_warning = "Сцена распознана как побережье/водоем, но в радиусе 1.2 км от сетки вода отсутствует. Применен проверенный водный якорь."
        except Exception:
            pass

    return final_lat, final_lon, final_method, sanity_warning


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


def geocode_osm_global(
    candidates: List[Any],
    is_indoor: bool = False,
    city_lat: Optional[float] = None,
    city_lon: Optional[float] = None,
    country_code: Optional[str] = None,
    region_mode: str = "global"
) -> Optional[Dict[str, Any]]:
    """Ищет адрес, название объекта или ТРЦ по карте (Nominatim + Overpass API) по всему миру или в режиме РК."""
    headers = {"User-Agent": "GeoSleuthGlobalResearch/3.2 (worldwide-indoor-protected)"}
    queries: List[str] = []
    for c in candidates:
        clean = re.sub(r"[^\w\s\-\.,№/а-яА-ЯёЁәіңғүұқөһӘІҢҒҮҰҚӨҺa-zA-Z0-9çÇşŞğĞıİöÖüÜéèàêëîïôûùñáíóú]", " ", str(c)).strip()
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
        deg = 25.0 / 111.32
        viewbox_params = {
            "viewbox": f"{city_lon - deg},{city_lat + deg},{city_lon + deg},{city_lat - deg}",
            "bounded": 0,
        }

    c_code = (country_code or "").strip().upper()
    if region_mode == "kz":
        c_code = "KZ"

    for q in queries[:12]:
        # 4. НЕЧЁТКИЙ МУЛЬТИ-ГЕОКОДЕР ДЛЯ OCR (Photon API)
        try:
            p_url = f"https://photon.komoot.io/api/?q={urllib.parse.quote(q)}&limit=3"
            if city_lat is not None and city_lon is not None:
                p_url += f"&lat={city_lat}&lon={city_lon}"
            pr = requests.get(p_url, headers=headers, timeout=5)
            if pr.ok:
                features = pr.json().get("features", [])
                for f in features:
                    coords = f.get("geometry", {}).get("coordinates", [])
                    if len(coords) >= 2:
                        p_lon = float(coords[0])
                        p_lat = float(coords[1])
                        props = f.get("properties", {})
                        p_name = props.get("name") or q
                        if city_lat is not None and city_lon is not None:
                            d_km = haversine_km(city_lat, city_lon, p_lat, p_lon)
                            if d_km > 65.0:
                                continue
                        return {
                            "lat": p_lat,
                            "lon": p_lon,
                            "name": p_name,
                            "matched_query": q,
                            "radius_m": 50 if is_indoor else 15,
                            "source": "photon"
                        }
        except Exception:
            pass

        try:
            params = {
                "q": q,
                "format": "jsonv2",
                "limit": 3,
                "addressdetails": 1,
                **viewbox_params
            }
            if c_code:
                params["countrycodes"] = c_code.lower()

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
            if city_lat is not None and city_lon is not None:
                overpass_q = f"""
                [out:json][timeout:8];
                (
                  node["name"~"{q}",i](around:35000,{city_lat},{city_lon});
                  way["name"~"{q}",i](around:35000,{city_lat},{city_lon});
                  relation["name"~"{q}",i](around:35000,{city_lat},{city_lon});
                );
                out center 3;
                """
            elif c_code:
                overpass_q = f"""
                [out:json][timeout:8];
                area["ISO3166-1"="{c_code}"]->.searchArea;
                (
                  node["name"~"{q}",i](area.searchArea);
                  way["name"~"{q}",i](area.searchArea);
                  relation["name"~"{q}",i](area.searchArea);
                );
                out center 3;
                """
            else:
                overpass_q = f"""
                [out:json][timeout:8];
                (
                  node["name"~"{q}",i];
                  way["name"~"{q}",i];
                  relation["name"~"{q}",i];
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
                                "name": el.get('tags', {}).get('name', q),
                                "matched_query": q,
                                "radius_m": 50 if is_indoor else 15,
                            }
            except Exception:
                pass
    return None


def geocode_in_kazakhstan(candidates: List[str], is_indoor: bool = False, city_lat: Optional[float] = None, city_lon: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """Алиас для обратной совместимости."""
    return geocode_osm_global(candidates, is_indoor=is_indoor, city_lat=city_lat, city_lon=city_lon, country_code="KZ", region_mode="kz")


search_ocr_osm = geocode_osm_global



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

    loc_enc: Any = getattr(model_obj, "gps_encoder", getattr(model_obj, "location_encoder", None))
    if loc_enc is None or not callable(loc_enc):
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
            loc_enc: Any = getattr(model_obj, "location_encoder", getattr(model_obj, "gps_encoder", None))
            if loc_enc is None or not callable(loc_enc):
                return {"status": "skipped", "lat": base_lat, "lon": base_lon, "radius_m": 250}
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


def locate_exact_spot(
    geoclip_model,
    image_path: str,
    city_lat: Optional[float] = None,
    city_lon: Optional[float] = None,
    region_mode: str = "global"
) -> Dict[str, Any]:
    """
    Главный конвейер геолокации мирового уровня (Zero-Mistake Worldwide Geolocation v3.5):
    1. Авто-очистка скриншотов и letterbox полей (preprocess_clean_internet_image).
    2. Локальная векторная память эталонов (visual_memory, мгновенный возврат при sim > 0.96).
    3. Инициализация галереи GeoCLIP с поддержкой режима 'global' (весь мир) или 'kz' (Казахстан).
    4. OpenCV эвристика интерьера с защитой ночных уличных фото (detect_indoor_cv).
    5. Gemini Vision с Google Search Grounding.
    6. Защита от галлюцинаций LLM: проверка и геокодирование через Wikipedia / Photon / Nominatim (verify_and_geocode_landmark).
    7. Универсальный парсер микро-признаков (международные телефонные коды, ccTLD, валюты + правила Казахстана).
    8. Пространственное пересечение брендов (Overpass API Brand Cluster -> точность 35м по всему миру).
    9. Адаптивный рельефный бустер: Алматинский горный пеленг / Terrain Bearing.
    10. Нечеткий мульти-геокодер OCR (Photon API + Nominatim).
    11. 5-кропный ансамбль с маскированием центрального объекта на GPU (точность до 15м).
    12. Агент-критик: семантическая самопроверка (semantic_sanity_check) против ложного дрейфа сетки.
    """
    # 0. Авто-очистка скриншотов и рамок соцсетей (letterbox)
    cleaned_pil = preprocess_clean_internet_image(image_path)
    active_image_path = image_path
    temp_cleaned_path = None
    try:
        orig_pil = Image.open(image_path)
        if cleaned_pil.size != orig_pil.size:
            temp_cleaned_path = str(Path(image_path).parent / f"cleaned_{Path(image_path).name}")
            cleaned_pil.save(temp_cleaned_path, "JPEG", quality=95)
            active_image_path = temp_cleaned_path
    except Exception:
        pass

    device = get_device()
    dhash = compute_image_dhash(cleaned_pil)
    query_emb = None
    if geoclip_model is not None:
        try:
            enrich_geoclip_gallery(geoclip_model, region_mode=region_mode)
            query_emb = extract_multiscale_image_embedding(geoclip_model, cleaned_pil, device)
        except Exception:
            pass

    # 0.5 Мгновенная проверка по локальной векторной памяти эталонов (dHash + 512-d Cosine)
    mem_hit = visual_memory.find_match(query_emb, dhash, sim_threshold=0.96, region_mode=region_mode)
    if mem_hit:
        street_views = fetch_mapillary_street_view(mem_hit["lat"], mem_hit["lon"])
        if temp_cleaned_path and os.path.exists(temp_cleaned_path):
            try:
                os.remove(temp_cleaned_path)
            except Exception:
                pass
        return {
            "exact_lat": mem_hit["lat"],
            "exact_lon": mem_hit["lon"],
            "radius_m": 15,
            "is_indoor": False,
            "country": mem_hit.get("country"),
            "country_code": None,
            "city": mem_hit.get("city"),
            "matched_label": mem_hit["name"],
            "method": f"Local Visual Memory ({mem_hit['match_type']}, sim={mem_hit['sim']:.3f}): {mem_hit['name']}",
            "confidence": mem_hit.get("confidence", 0.99),
            "street_view_matches": street_views,
            "diagnostics": {"memory_match": mem_hit}
        }

    # 1. Локальная эвристика интерьера с защитой ночной улицы
    cv_indoor = detect_indoor_cv(active_image_path)
    is_indoor = cv_indoor.get("is_indoor_heuristic", False)
    is_night_outdoor = cv_indoor.get("is_night_outdoor", False)

    # 2. Gemini Vision с Google Search Grounding
    vlm = analyze_with_gemini_vision(active_image_path)
    vlm_data = vlm.get("data", {}) if isinstance(vlm.get("data"), dict) else {}

    detected_country = vlm_data.get("country")
    detected_country_code = vlm_data.get("country_code")
    detected_city = vlm_data.get("city")

    if vlm_data.get("is_indoor") is not None:
        if is_night_outdoor and not vlm_data.get("is_indoor"):
            is_indoor = False
        else:
            is_indoor = bool(vlm_data.get("is_indoor"))

    # 3. Извлекаем OCR текст и микро-признаки (мировые + Казахстан)
    ocr_texts = extract_text_from_photo(active_image_path, is_indoor=is_indoor)
    all_texts = ocr_texts + vlm_data.get("detected_text", [])
    clues = extract_global_and_kz_clues(all_texts)

    if not detected_country and clues.get("country"):
        detected_country = clues["country"]
        detected_country_code = clues["country_code"]
    if not detected_city and clues.get("inferred_city"):
        detected_city = clues["inferred_city"]

    # 4. ЗАЩИТА ОТ ГАЛЛЮЦИНАЦИИ ЦИФР LLM: проверка и геокодирование через Wikipedia / Photon / Nominatim
    vlm_place = vlm_data.get("place_name")
    vlm_lat_val = float(vlm_data["lat"]) if vlm_data.get("lat") is not None else None
    vlm_lon_val = float(vlm_data["lon"]) if vlm_data.get("lon") is not None else None

    verified_landmark = verify_and_geocode_landmark(
        name=vlm_place,
        city=detected_city,
        country=detected_country,
        llm_lat=vlm_lat_val,
        llm_lon=vlm_lon_val
    )
    if verified_landmark and verified_landmark.get("lat") and verified_landmark.get("lon"):
        vl_lat = float(verified_landmark["lat"])
        vl_lon = float(verified_landmark["lon"])
        vl_name = verified_landmark.get("name", vlm_place or "")
        vl_src = verified_landmark.get("source", "Geocoder")
        street_views = fetch_mapillary_street_view(vl_lat, vl_lon)
        visual_memory.add_entry(query_emb, dhash, vl_lat, vl_lon, name=vl_name, country=detected_country, city=detected_city)
        if temp_cleaned_path and os.path.exists(temp_cleaned_path):
            try:
                os.remove(temp_cleaned_path)
            except Exception:
                pass
        return {
            "exact_lat": vl_lat,
            "exact_lon": vl_lon,
            "radius_m": 20,
            "is_indoor": is_indoor,
            "country": detected_country,
            "country_code": detected_country_code,
            "city": detected_city,
            "matched_label": vl_name,
            "method": f"Verified Landmark Geocode ({vl_src}): {vl_name}",
            "street_view_matches": street_views,
            "diagnostics": {
                "verified_landmark": verified_landmark,
                "gemini_vision": vlm_data,
                "clues": clues,
                "cv_indoor": cv_indoor
            }
        }

    # 5. Динамический выбор базового якоря (city_lat, city_lon) БЕЗ сваливания в Алматы
    if vlm.get("status") == "ok" and vlm_lat_val is not None and vlm_lon_val is not None and float(vlm_data.get("confidence", 0)) >= 0.65:
        city_lat = vlm_lat_val
        city_lon = vlm_lon_val
    elif clues.get("anchor_lat") and clues.get("anchor_lon") and clues.get("confidence", 0) >= 0.70:
        if city_lat is None or city_lon is None or (region_mode == "kz" and not (40.0 <= city_lat <= 56.0 and 46.0 <= city_lon <= 88.0)):
            city_lat = clues["anchor_lat"]
            city_lon = clues["anchor_lon"]
    elif city_lat is None or city_lon is None:
        if geoclip_model is not None and hasattr(geoclip_model, "predict"):
            try:
                preds_top, _ = geoclip_model.predict(active_image_path, top_k=1)
                city_lat = float(preds_top[0][0])
                city_lon = float(preds_top[0][1])
            except Exception:
                pass
        if city_lat is None or city_lon is None:
            city_lat = 43.2389 if region_mode == "kz" else 48.8584
            city_lon = 76.8897 if region_mode == "kz" else 2.2945

    # 6. Window View Analysis: если из окна видны горы или знаковые высотки
    window_view = vlm_data.get("window_view", {})
    if window_view.get("has_window_view") and window_view.get("window_landmarks"):
        window_queries = [str(lm) for lm in window_view["window_landmarks"] if lm]
        win_hit = geocode_osm_global(
            window_queries,
            is_indoor=False,
            city_lat=city_lat,
            city_lon=city_lon,
            country_code=detected_country_code,
            region_mode=region_mode
        )
        if win_hit:
            street_views = fetch_mapillary_street_view(win_hit["lat"], win_hit["lon"])
            visual_memory.add_entry(query_emb, dhash, win_hit["lat"], win_hit["lon"], name=win_hit["name"], country=detected_country, city=detected_city)
            if temp_cleaned_path and os.path.exists(temp_cleaned_path):
                try:
                    os.remove(temp_cleaned_path)
                except Exception:
                    pass
            return {
                "exact_lat": win_hit["lat"],
                "exact_lon": win_hit["lon"],
                "radius_m": 75,
                "is_indoor": is_indoor,
                "country": detected_country,
                "country_code": detected_country_code,
                "city": detected_city,
                "matched_label": f"Вид из окна на {win_hit['name']}",
                "method": f"Window View Landmark: «{win_hit['matched_query']}»",
                "street_view_matches": street_views,
                "diagnostics": {
                    "gemini_vision": vlm_data,
                    "window_view": window_view,
                    "osm_refined": win_hit,
                    "clues": clues,
                    "cv_indoor": cv_indoor
                }
            }

    # 7. Пространственное пересечение брендов (Overpass API Brand Cluster -> 35м) по всему миру
    if is_indoor and city_lat is not None and city_lon is not None:
        brand_candidates = []
        for b in vlm_data.get("search_queries", []) + ocr_texts + vlm_data.get("detected_text", []):
            if b and str(b).lower() not in INDOOR_OCR_STOPWORDS:
                brand_candidates.append(str(b))

        brand_cluster = search_overpass_brand_cluster(brand_candidates, city_lat, city_lon, radius_m=15000, cluster_radius_m=120)
        if brand_cluster:
            street_views = fetch_mapillary_street_view(brand_cluster["lat"], brand_cluster["lon"])
            visual_memory.add_entry(query_emb, dhash, brand_cluster["lat"], brand_cluster["lon"], name=brand_cluster["name"], country=detected_country, city=detected_city)
            if temp_cleaned_path and os.path.exists(temp_cleaned_path):
                try:
                    os.remove(temp_cleaned_path)
                except Exception:
                    pass
            return {
                "exact_lat": brand_cluster["lat"],
                "exact_lon": brand_cluster["lon"],
                "radius_m": 35,
                "is_indoor": True,
                "country": detected_country,
                "country_code": detected_country_code,
                "city": detected_city,
                "scene_type": vlm_data.get("scene_type", "mall"),
                "matched_label": brand_cluster["name"],
                "method": "Indoor Brand Cluster (Overpass)",
                "street_view_matches": street_views,
                "diagnostics": {
                    "brand_cluster": brand_cluster,
                    "gemini_vision": vlm_data,
                    "clues": clues,
                    "cv_indoor": cv_indoor
                }
            }

    # 8. Адаптивный рельефный бустер: Алматинский горный пеленг (только для окрестностей Алматы)
    almaty_mountain = vlm_data.get("almaty_mountain_bearing", {})
    general_terrain = vlm_data.get("terrain_bearing", {})

    is_almaty_area = (
        (city_lat is not None and city_lon is not None and 43.00 <= city_lat <= 43.55 and 76.60 <= city_lon <= 77.25)
        or (detected_city and "almaty" in str(detected_city).lower())
        or (region_mode == "kz" and city_lat is not None and 43.0 <= city_lat <= 43.6)
    )

    almaty_sector_applied = None
    if is_almaty_area and isinstance(almaty_mountain, dict) and almaty_mountain.get("city_sector"):
        sector_name = almaty_mountain.get("city_sector")
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
            if not (vlm.get("status") == "ok" and vlm_lat_val is not None and float(vlm_data.get("confidence", 0)) >= 0.75):
                city_lat = sector_lat
                city_lon = sector_lon

    # 9. Поиск известных ТРЦ/аэропортов/станций по названиям брендов
    if is_indoor and vlm_data.get("search_queries"):
        indoor_osm_hit = geocode_osm_global(
            vlm_data.get("search_queries"),
            is_indoor=True,
            city_lat=city_lat,
            city_lon=city_lon,
            country_code=detected_country_code,
            region_mode=region_mode
        )
        if indoor_osm_hit:
            street_views = fetch_mapillary_street_view(indoor_osm_hit["lat"], indoor_osm_hit["lon"])
            visual_memory.add_entry(query_emb, dhash, indoor_osm_hit["lat"], indoor_osm_hit["lon"], name=indoor_osm_hit["name"], country=detected_country, city=detected_city)
            if temp_cleaned_path and os.path.exists(temp_cleaned_path):
                try:
                    os.remove(temp_cleaned_path)
                except Exception:
                    pass
            return {
                "exact_lat": indoor_osm_hit["lat"],
                "exact_lon": indoor_osm_hit["lon"],
                "radius_m": 50,
                "is_indoor": True,
                "country": detected_country,
                "country_code": detected_country_code,
                "city": detected_city,
                "scene_type": vlm_data.get("scene_type", "indoor"),
                "matched_label": indoor_osm_hit["name"],
                "method": f"Indoor Landmark Search: «{indoor_osm_hit['matched_query']}»",
                "street_view_matches": street_views,
                "diagnostics": {
                    "gemini_vision": vlm_data,
                    "matched_poi": indoor_osm_hit,
                    "clues": clues,
                    "cv_indoor": cv_indoor
                }
            }

    # 10. Локальный OCR поиск по вывескам/табличкам через нечеткий мульти-геокодер (Photon + Nominatim)
    ocr_hit = geocode_osm_global(
        ocr_texts,
        is_indoor=is_indoor,
        city_lat=city_lat,
        city_lon=city_lon,
        country_code=detected_country_code,
        region_mode=region_mode
    )
    if ocr_hit:
        street_views = fetch_mapillary_street_view(ocr_hit["lat"], ocr_hit["lon"])
        visual_memory.add_entry(query_emb, dhash, ocr_hit["lat"], ocr_hit["lon"], name=ocr_hit["name"], country=detected_country, city=detected_city)
        if temp_cleaned_path and os.path.exists(temp_cleaned_path):
            try:
                os.remove(temp_cleaned_path)
            except Exception:
                pass
        return {
            "exact_lat": ocr_hit["lat"],
            "exact_lon": ocr_hit["lon"],
            "radius_m": 50 if is_indoor else 15,
            "is_indoor": is_indoor,
            "country": detected_country,
            "country_code": detected_country_code,
            "city": detected_city,
            "matched_label": ocr_hit["name"],
            "method": f"OCR Text/Address Match: «{ocr_hit['matched_query']}»",
            "street_view_matches": street_views,
            "diagnostics": {
                "ocr_texts": ocr_texts,
                "matched_place": ocr_hit,
                "clues": clues,
                "is_indoor": is_indoor,
                "gemini_status": vlm
            }
        }

    # 11. GeoCLIP доводка с 5-кропной ультраплотной сеткой на GPU
    c_lat: float = float(city_lat) if city_lat is not None else (43.2389 if region_mode == "kz" else 48.8584)
    c_lon: float = float(city_lon) if city_lon is not None else (76.8897 if region_mode == "kz" else 2.2945)
    grid_res = refine_dense_grid(geoclip_model, active_image_path, c_lat, c_lon, is_indoor=is_indoor)

    candidate_lat = float(grid_res.get("lat", c_lat))
    candidate_lon = float(grid_res.get("lon", c_lon))

    # Динамическое именование метода с указанием страны
    country_display = detected_country or (clues.get("country") if clues else None)
    if not country_display or str(country_display).lower() in ("null", "none", "unknown"):
        country_display = "Global"

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
        street_views = fetch_mapillary_street_view(candidate_lat, candidate_lon)
    else:
        method_name = f"{country_display} Outdoor GPU Grid (15m)"
        warning_msg = None
        street_views = fetch_mapillary_street_view(candidate_lat, candidate_lon)

    # 12. Агент-критик: семантическая самопроверка (semantic_sanity_check)
    final_lat, final_lon, final_method, sanity_warn = semantic_sanity_check(
        candidate_lat=candidate_lat,
        candidate_lon=candidate_lon,
        vlm_data=vlm_data,
        clues=clues,
        verified_landmark=verified_landmark,
        anchor_lat=c_lat,
        anchor_lon=c_lon,
        method_name=method_name
    )
    if sanity_warn:
        warning_msg = f"{warning_msg + ' | ' if warning_msg else ''}{sanity_warn}"
        street_views = fetch_mapillary_street_view(final_lat, final_lon)

    # Сохраняем проверенную точку в визуальную память
    visual_memory.add_entry(
        emb_vector=query_emb,
        dhash=dhash,
        lat=final_lat,
        lon=final_lon,
        name=detected_city or country_display,
        country=detected_country,
        city=detected_city
    )

    if temp_cleaned_path and os.path.exists(temp_cleaned_path):
        try:
            os.remove(temp_cleaned_path)
        except Exception:
            pass

    return {
        "exact_lat": final_lat,
        "exact_lon": final_lon,
        "radius_m": grid_res.get("radius_m", 2500 if is_indoor else 15),
        "is_indoor": is_indoor,
        "country": detected_country,
        "country_code": detected_country_code,
        "city": detected_city,
        "matched_label": None,
        "method": final_method,
        "warning": warning_msg,
        "street_view_matches": street_views,
        "diagnostics": {
            "country": detected_country,
            "country_code": detected_country_code,
            "city": detected_city,
            "is_indoor": is_indoor,
            "cv_indoor": cv_indoor,
            "clues": clues,
            "gemini_status": vlm,
            "terrain_bearing": general_terrain,
            "almaty_mountain_bearing": almaty_mountain,
            "ocr_texts": ocr_texts,
            "dense_grid": grid_res,
            "sanity_check": sanity_warn
        },
    }

