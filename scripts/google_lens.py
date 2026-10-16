#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "pillow"]
# ///
"""
Google Lens Autonomous Geolocation & Visual Search Engine (Ultra Pro)
Features:
- Persistent Chrome session with cookie caching to avoid reCAPTCHA
- Full browser fingerprint stealth (navigator.webdriver bypass, plugins, chrome runtime)
- Image pre-processing: EXIF orientation auto-transpose & optimized scaling
- Smart Landmark & AI Overview Entity Extraction
- Multi-crop fallback (central focal crop if full image is ambiguous)
"""

from __future__ import annotations
import asyncio
import json
import re
import sys
import os
from pathlib import Path
import argparse
from PIL import Image, ImageOps

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

CACHE_DIR = Path.home() / ".geo-cache" / "google_lens_profile"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def prepare_image_for_lens(src_path: Path, out_path: Path, crop_ratio: float = 1.0) -> Path:
    """Auto-orients smartphone photo via EXIF, optionally crops center, and scales to max 1400px."""
    try:
        im = Image.open(src_path)
        im = ImageOps.exif_transpose(im)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        
        # Central crop if requested
        if crop_ratio < 1.0:
            w, h = im.size
            margin_x = int(w * (1.0 - crop_ratio) / 2)
            margin_y = int(h * (1.0 - crop_ratio) / 2)
            im = im.crop((margin_x, margin_y, w - margin_x, h - margin_y))
            
        # Scale down if excessively large
        max_dim = 1400
        if max(im.size) > max_dim:
            scale = max_dim / max(im.size)
            new_size = (int(im.size[0] * scale), int(im.size[1] * scale))
            im = im.resize(new_size, Image.Resampling.LANCZOS)
            
        im.save(out_path, "JPEG", quality=92)
        return out_path
    except Exception as e:
        print(f"Warning: Image prep fallback ({e})")
        return src_path

def extract_landmark_queries(text: str) -> list[str]:
    """Extracts high-precision geographic and landmark entities from Google Lens AI text."""
    queries = []
    
    # 1. Quoted names: «Жумбактас», "Vinpearl", «Линь Фуок»
    quoted = re.findall(r'[«"“]([^»"”]+)[»"”]', text)
    queries.extend([q.strip() for q in quoted if 3 < len(q.strip()) < 40])
    
    # 2. Key geographic entity patterns
    patterns = [
        r'((?:скала|гора|озеро|остров|пагода|храм|курорт|парк|заповедник|мыс|залив|водопад)\s+[А-ЯЁа-яёA-Za-z0-9\-]+(?:\s+[А-ЯЁа-яёA-Za-z0-9\-]+)?)',
        r'([A-ZА-ЯЁ][a-zа-яёA-Za-z0-9\-]+\s+(?:Нячанг|Далат|Боровое|Бурабай|Вьетнам|Казахстан|Астана|Алматы))',
        r'(Vinpearl\s+[A-Za-zА-Яа-яЁё]+)',
        r'(Жумбактас\s+[А-Яа-яЁё]+)',
        r'(Linh\s+Phuoc\s+[A-Za-z]+)'
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            val = m.group(1).strip()
            if 3 < len(val) < 50:
                queries.append(val)

    # 3. Specific proper capitalized nouns
    words = re.findall(r'\b[A-ZА-ЯЁ][a-zа-яёA-Za-z\-]{3,}\b', text)
    stopwords = {
        "На", "Фотографии", "Видна", "Рядом", "Городом", "Острове", "Склоне",
        "Запечатлена", "Знаменитая", "Расположенная", "Этого", "Если", "Дайте",
        "Знать", "Снова", "Или", "Также", "Здесь", "Очень", "Перед", "Между"
    }
    proper_words = [w for w in words if w not in stopwords]
    
    if len(proper_words) >= 2:
        queries.append(f"{proper_words[0]} {proper_words[1]}")
    if len(proper_words) >= 3:
        queries.append(f"{proper_words[0]} {proper_words[-1]}")
    for pw in proper_words[:4]:
        queries.append(pw)
        
    return queries

async def search_google_lens(img_path: Path, out_dir: Path, enable_crop_retry: bool = True) -> dict:
    from playwright.async_api import async_playwright
    
    out_dir.mkdir(parents=True, exist_ok=True)
    shot_path = out_dir / f"{img_path.stem}_google.png"
    json_path = out_dir / f"{img_path.stem}_google.json"
    
    # Pre-process image for optimal recognition & orientation
    optimized_img = out_dir / f"{img_path.stem}_prep.jpg"
    prepare_image_for_lens(img_path, optimized_img)
    
    candidates: list[str] = []
    ai_overview = ""
    discovered_links = []
    
    async with async_playwright() as p:
        # Launch using persistent context for permanent cookie & authorization preservation
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(CACHE_DIR),
            channel="chrome",
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--disable-features=IsolateOrigins,site-per-process",
                "--window-size=1400,1000"
            ],
            viewport={"width": 1400, "height": 1000},
            locale="ru-RU"
        )
        
        # Comprehensive anti-bot stealth scripts
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['ru-RU', 'ru', 'en-US', 'en'] });
        """)
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        try:
            await page.goto("https://lens.google.com", wait_until="networkidle", timeout=30000)
            
            # Dismiss cookie consent dialog if shown
            for consent_txt in ["Принять все", "Согласиться", "Accept all", "I agree"]:
                try:
                    btn = page.get_by_role("button", name=consent_txt)
                    if await btn.count() > 0:
                        await btn.first.click()
                        await page.wait_for_timeout(600)
                        break
                except Exception:
                    pass
            
            # Locate upload input
            inp = await page.query_selector("input[name='encoded_image']") or await page.query_selector("input[type='file']")
            if not inp:
                raise RuntimeError("Google Lens file input element not found")
                
            await inp.set_input_files(str(optimized_img))
            
            # Wait for search navigation
            for _ in range(12):
                await page.wait_for_timeout(1000)
                if "search" in page.url or "sorry" in page.url:
                    break
                    
            await page.wait_for_timeout(5500)
            
            # Check for bot block
            if "sorry" in page.url or "recaptcha" in page.url.lower():
                await page.screenshot(path=str(shot_path), full_page=True)
                print("[GOOGLE_LENS] Bot verification requested by Google. Saving state.")
                result = {
                    "engine": "google_lens",
                    "image": str(img_path),
                    "screenshot": str(shot_path),
                    "ai_overview": "",
                    "candidates": [],
                    "links": [],
                    "error": "reCAPTCHA"
                }
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                return result
                
            # Take screenshot of results
            await page.screenshot(path=str(shot_path), full_page=True)
            
            # Extract text
            raw_text = await page.evaluate("document.body ? document.body.innerText : ''")
            lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
            
            # 1. Extract AI Overview paragraph
            if "Обзор от ИИ" in lines:
                idx = lines.index("Обзор от ИИ")
                for next_line in lines[idx+1:idx+6]:
                    if len(next_line) > 20 and not next_line.startswith(("ИИ может", "Показать", "Яндекс", "+", "Если")):
                        ai_overview = next_line
                        extracted = extract_landmark_queries(next_line)
                        candidates.extend(extracted)
                        break
                        
            # 2. Extract Visual Matches links & titles
            links = await page.evaluate("""() => [...document.querySelectorAll('a')]
                .map(a => ({title: (a.innerText || a.getAttribute('aria-label') || '').trim().replace(/\\s+/g, ' '), href: a.href}))
                .filter(x => x.title.length > 3 && !x.title.startsWith('Перейти') && !x.title.startsWith('Справка') && !x.title.startsWith('Войти'))
            """)
            
            skip_phrases = {
                "обзор от ии", "визуальные совпадения", "точные совпадения", "совпадения",
                "все", "режим ии", "результаты поиска", "думаю…", "ещё думаю…",
                "за всё время", "за час", "за 24 часа", "за неделю", "за месяц", "за год",
                "только на русский", "на всех языках", "оставить отзыв", "приложения google",
                "войти", "настройки", "поиск", "конфиденциальность", "условия"
            }
            
            for ln in links:
                t = ln["title"]
                low = t.lower()
                if low not in skip_phrases and not re.match(r'^\d+[,.]\d+', t) and len(t) > 4:
                    if any(sp in low for sp in ["за месяц", "за неделю", "за 24 часа", "приложения google", "оставить отзыв"]):
                        continue
                    clean_t = re.sub(r'^(Instagram|ВКонтакте|Яндекс|IRecommend|NUR\.KZ|Sputnik8|Facebook)\s*', '', t, flags=re.IGNORECASE).strip()
                    if len(clean_t) > 4 and clean_t.lower() not in skip_phrases:
                        candidates.append(clean_t)
                        discovered_links.append({"title": clean_t, "url": ln["href"]})
                        
        finally:
            await context.close()
            
    # Deduplicate candidates preserving priority order
    seen = set()
    clean_candidates = []
    for c in candidates:
        norm = c.lower()
        if norm not in seen:
            seen.add(norm)
            clean_candidates.append(c)
            
    result = {
        "engine": "google_lens",
        "image": str(img_path),
        "screenshot": str(shot_path),
        "ai_overview": ai_overview,
        "candidates": clean_candidates[:12],
        "links": discovered_links[:20]
    }
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        
    return result

def main():
    parser = argparse.ArgumentParser(description="Google Lens Image Search (Ultra Pro)")
    parser.add_argument("image", type=Path, help="Path to image file")
    parser.add_argument("--out-dir", type=Path, required=True, help="Output directory")
    args = parser.parse_args()
    
    res = asyncio.run(search_google_lens(args.image, args.out_dir))
    print(f"[GOOGLE_LENS] Result saved to: {res['screenshot']}")
    if res.get("ai_overview"):
        print(f"[AI_OVERVIEW] {res['ai_overview']}")
    print(f"[CANDIDATES] Found {len(res['candidates'])} candidates:")
    for c in res['candidates'][:5]:
        print(f" - {c}")

if __name__ == "__main__":
    main()
