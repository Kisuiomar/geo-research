import re
import urllib.parse
import urllib.request
import json

def extract_high_value_poi_queries(text: str) -> list[str]:
    cands = []
    # 1. Quoted text: "Золотое Яблоко", «MEGA Silk Way»
    quotes = re.findall(r'[«"“]([^»"”]+)[»"”]', text)
    for q in quotes:
        clean = q.strip()
        if 2 < len(clean) < 50:
            cands.append(clean)
            
    # 2. Known complexes / malls / landmarks / chains
    complex_patterns = [
        r'\b(MEGA\s+[A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)?)\b',
        r'\b(ТРЦ\s+[А-Яа-яA-Za-z0-9\-]+(?:\s+[А-Яа-яA-Za-z0-9\-]+)?)\b',
        r'\b(ТЦ\s+[А-Яа-яA-Za-z0-9\-]+(?:\s+[А-Яа-яA-Za-z0-9\-]+)?)\b',
        r'\b(Silk\s+Way(?:\s+[A-Za-z0-9]+)?)\b',
        r'\b(Золотое\s+Яблоко)\b',
        r'\b(Хан\s+Шатыр)\b',
        r'\b(Abu\s+Dhabi\s+Plaza)\b',
        r'\b(Dostyk\s+Plaza)\b',
        r'\b(Esentai\s+Mall)\b',
        r'\b(Aport\s+Mall)\b',
        r'\b(Керуен(?:\s+City)?)\b',
        r'\b(Астана\s+Молл)\b',
        r'\b(Сарыарка)\b'
    ]
    for pat in complex_patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            val = m.group(1).strip()
            if val not in cands:
                cands.append(val)
                
    # 3. Detect city in text (Астана, Алматы, Шымкент, etc.)
    city_match = None
    for city in ["Астана", "Алматы", "Шымкент", "Караганда", "Актобе", "Атырау", "Актау", "Павлодар"]:
        if re.search(r'\b' + city[:5] + r'[а-я]*\b', text, re.IGNORECASE):
            city_match = city
            break
            
    # 4. Combine top entities with city
    if city_match:
        for base in list(cands):
            combo = f"{base} {city_match}"
            if combo not in cands:
                cands.insert(0, combo)
                
    # 5. Clean up news title
    clean_title = re.sub(r'[:\-–—]\s*(?:новости|фото|видео|tengrinews|zakon|nur|inform|kursiv|kapital).*$', '', text, flags=re.IGNORECASE)
    clean_title = re.sub(r'\b(?:открылся|появился|работает|первый|новый|супермаркет|магазин|новости|вчера|сегодня)\b', ' ', clean_title, flags=re.IGNORECASE)
    clean_title = re.sub(r'[\(\)\[\]«»"\'\?!\*:,•@$]', ' ', clean_title).strip()
    words = [w for w in clean_title.split() if len(w) > 2 and w.lower() not in ("для", "при", "все", "или", "как", "рынок", "выхода")]
    if len(words) >= 2:
        cands.append(" ".join(words[:4]))
        if len(words) >= 3:
            cands.append(" ".join(words[:3]))
            
    return cands

t = 'В MEGA Silk Way открылся первый супермаркет "Золотое Яблоко" в Астане: 23 июня 2023 13:00 - новости на Tengrinews.kz'
cands = extract_high_value_poi_queries(t)
print("Extracted candidates:", cands)

for c in cands:
    u = 'https://photon.komoot.io/api/?q=' + urllib.parse.quote(c) + '&lat=51.169392&lon=71.449074&limit=3'
    req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=5).read().decode('utf-8'))
        feats = data.get('features', [])
        for f in feats:
            props = f.get('properties', {})
            country = (props.get('country') or '').lower()
            if 'kazakhstan' in country or 'казахстан' in country or 'қазақстан' in country:
                print(f"MATCH: cand='{c}' -> {props.get('name')} in {props.get('city')}, coords={f['geometry']['coordinates']}")
                break
    except Exception as e:
        print("Error:", e)
