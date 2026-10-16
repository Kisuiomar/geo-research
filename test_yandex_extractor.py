import json
from pathlib import Path
import re

yandex_file = Path("web/static/uploads/rev_30a58482/3123bbc5_yandex.json")
with open(yandex_file, "r", encoding="utf-8") as f:
    ydata = json.load(f)

DISQUALIFIED_PHRASES = {
    "обзор от ии", "визуальные совпадения", "точные совпадения", "совпадения",
    "все", "режим ии", "результаты поиска", "думаю…", "ещё думаю…",
    "за всё время", "за час", "за 24 часа", "за неделю", "за месяц", "за год",
    "только на русский", "на всех языках", "оставить отзыв", "приложения google",
    "войти", "настройки", "поиск", "конфиденциальность", "условия", "показать еще",
    "яндекс", "умная камера", "двигайте рамки", "похожие", "больше похожих", "сайты",
    "все результаты", "точное соответствие"
}

GENERIC_CLASSIFIERS = {
    "бизнес центры", "бизнес центр", "бизнес-центры", "бизнес-центр",
    "торговые центры", "торговый центр", "торговые комплексы", "торговый комплекс",
    "здание", "здания", "небоскреб", "небоскребы", "строение", "постройка", "постройки",
    "город", "города", "улица", "улицы", "проспект", "проспекты", "площадь", "площади",
    "архитектура", "фасад", "фасады", "интерьер", "интерьеры", "помещение", "помещения",
    "зал", "залы", "магазин", "магазины", "супермаркет", "супермаркеты", "бутик", "бутики",
    "парк", "парки", "озеро", "озера", "гора", "горы", "дерево", "деревья",
    "природа", "пейзаж", "пейзажи", "панорама", "панорамы", "туризм",
    "достопримечательность", "достопримечательности", "комната", "офис", "офисы",
    "коридор", "люди", "человек", "визуальные совпадения", "жилой комплекс", "жк", "дом", "дома"
}

def extract_yandex_vision_intel(ydata: dict) -> dict:
    intel = {
        "entity_card": None,
        "entity_candidates": [],
        "map_addresses": [],
        "specific_tags": [],
        "city_hints": [],
        "all_ranked_candidates": []
    }
    th = ydata.get("text_head", "")
    if not th:
        return intel

    lines = [l.strip() for l in th.split("\n") if l.strip()]

    city_candidate = None
    title_candidate = None
    desc_candidate = None

    if "Кажется, на изображении" in lines:
        k_idx = lines.index("Кажется, на изображении")
        pre_lines = lines[:k_idx]
        clean_pre = [
            l for l in pre_lines 
            if l.lower() not in DISQUALIFIED_PHRASES 
            and not any(ui in l.lower() for ui in ["войти", "поиск", "картинки", "видео", "карты", "переводчик", "умная камера", "двигайте", "нейро"])
            and not re.match(r'^[a-z0-9\-]+\.[a-z]{2,}', l.lower())
        ]
        
        for line in clean_pre:
            if len(line) < 30 and any(c.lower() in line.lower() for c in ["астана", "алматы", "шымкент", "караганда", "актобе", "казахстан", "россия", "вьетнам", "далат", "нячанг"]):
                city_candidate = line
            elif not title_candidate and len(line) < 80 and not line.endswith("..."):
                title_candidate = line
            elif not desc_candidate and len(line) > 30:
                desc_candidate = line

        if title_candidate:
            intel["entity_card"] = {
                "title": title_candidate,
                "city": city_candidate or "",
                "desc": desc_candidate or ""
            }
            if city_candidate and city_candidate.lower() not in title_candidate.lower():
                intel["entity_candidates"].append(f"{title_candidate} {city_candidate}".strip())
            intel["entity_candidates"].append(title_candidate)

        for t in lines[k_idx+1:k_idx+8]:
            t_clean = t.strip()
            if t_clean in ("Похожие", "Больше похожих", "Сайты", "Копии") or len(t_clean) < 3:
                continue
            if t_clean.lower() in GENERIC_CLASSIFIERS or t_clean.lower() in DISQUALIFIED_PHRASES:
                continue
            intel["specific_tags"].append(t_clean)
            if city_candidate and city_candidate.lower() not in t_clean.lower():
                intel["specific_tags"].append(f"{t_clean} {city_candidate}".strip())

    for line in lines:
        if any(ym in line.lower() for ym in ["яндекс карты", "яндекс.карты", "yandex maps", "yandex.maps"]):
            cleaned = re.sub(r'[\-–—]\s*(?:яндекс\s*карты|yandex\s*maps).*$', '', line, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r'^(?:панорама|фото|отзывы|reviews)\s*:\s*', '', cleaned, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r'^\d+×\d+\s*', '', cleaned).strip()
            if len(cleaned) > 5:
                intel["map_addresses"].append(cleaned)
                st_match = re.search(r'([А-Яа-яA-Za-z\s]+(?:даңғылы|просп|проспект|көшесі|улица|ул)[^\,]*\,?\s*(?:C?\d+[\/\d\w]*))', cleaned, re.IGNORECASE)
                if st_match:
                    addr_cand = st_match.group(1).strip()
                    if city_candidate and city_candidate.lower() not in addr_cand.lower():
                        addr_cand = f"{city_candidate}, {addr_cand}"
                    if addr_cand not in intel["map_addresses"]:
                        intel["map_addresses"].insert(0, addr_cand)

    # Combine into ranked list
    ranked = []
    for c in intel["entity_candidates"] + intel["map_addresses"] + intel["specific_tags"]:
        if c and c not in ranked:
            ranked.append(c)
    intel["all_ranked_candidates"] = ranked
    return intel

res = extract_yandex_vision_intel(ydata)
print("Entity card:", res["entity_card"])
print("Entity candidates:", res["entity_candidates"])
print("Map addresses:", res["map_addresses"])
print("Specific tags:", res["specific_tags"])
print("Ranked candidates:", res["all_ranked_candidates"])
