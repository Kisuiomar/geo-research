#!/usr/bin/env python3
"""Executive One-Page OSINT Evidence Sheet Compositor.

Adapted and enhanced from Geo-Guesser and GeoLens.
Generates an exportable high-resolution forensic summary dossier image
combining photo, satellite verification, clues, coordinates, and confidence.
"""
from __future__ import annotations

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

CANVAS_WIDTH = 1600
PADDING = 24
HEADER_HEIGHT = 80
BG_COLOR = (15, 23, 42)        # Dark slate
CARD_BG = (30, 41, 59)         # Navy slate card
ACCENT_COLOR = (14, 165, 233)   # Sky cyan
SUCCESS_COLOR = (34, 197, 94)  # Emerald green
TEXT_MAIN = (248, 250, 252)    # Pure off-white
TEXT_MUTED = (148, 163, 184)   # Slate gray
BORDER_COLOR = (51, 65, 85)

def get_font(size: int, bold: bool = False):
    font_paths = [
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\segoeuib.ttf" if bold else "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\tahoma.ttf"
    ]
    for p in font_paths:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def wrap_text(text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines = []
    current = ""
    for w in words:
        test = (current + " " + w).strip()
        # Fallback bounding box check
        try:
            bbox = font.getbbox(test)
            w_px = bbox[2] - bbox[0]
        except AttributeError:
            w_px = len(test) * 9
        if w_px <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines

def compose_evidence_sheet(case_data: dict, static_dir: Path, out_path: Path) -> Path:
    """Renders a single high-resolution OSINT Evidence Dossier Image."""
    f_title = get_font(28, bold=True)
    f_sub = get_font(18, bold=False)
    f_heading = get_font(20, bold=True)
    f_body = get_font(16, bold=False)
    f_mono = get_font(18, bold=True)

    title = case_data.get("title", "OSINT Geolocation Case")
    target_name = case_data.get("target_name", "Объект")
    region = case_data.get("region", "Казахстан")
    confidence = case_data.get("confidence", "VERIFIED")
    lat = case_data.get("target_lat", 0.0)
    lon = case_data.get("target_lon", 0.0)
    desc = case_data.get("description", "")
    clues = case_data.get("clues", [])

    # Load photos
    main_photo_rel = case_data.get("main_photo", "").lstrip("/")
    main_photo_path = static_dir.parent / main_photo_rel if main_photo_rel else None

    # Find satellite and evidence photos
    sat_photo_path = None
    ev_photo_path = None
    for ev in case_data.get("evidence_photos", []):
        url = ev.get("url", "").lstrip("/")
        p = static_dir.parent / url
        if p.exists():
            if "sat_" in p.name:
                sat_photo_path = p
            elif not ev_photo_path and "google" in p.name or "yandex" in p.name:
                ev_photo_path = p

    # Determine layout
    row_height = 420
    content_width = CANVAS_WIDTH - (2 * PADDING)
    card_width = (content_width - PADDING) // 2

    # Canvas height calculation
    desc_lines = wrap_text(desc, f_body, content_width - 40)
    clue_lines_count = sum(len(wrap_text(c, f_body, content_width - 80)) for c in clues[:6])
    info_box_height = 140 + (len(desc_lines) * 24) + (clue_lines_count * 24)
    canvas_height = HEADER_HEIGHT + PADDING + row_height + PADDING + info_box_height + PADDING

    canvas = Image.new("RGB", (CANVAS_WIDTH, canvas_height), BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    # 1. Header Banner
    draw.rectangle([0, 0, CANVAS_WIDTH, HEADER_HEIGHT], fill=(15, 23, 42))
    draw.line([(0, HEADER_HEIGHT), (CANVAS_WIDTH, HEADER_HEIGHT)], fill=BORDER_COLOR, width=2)
    draw.text((PADDING, 16), "GEOSLEUTH INTEL HUB · ФОРЕНЗИЧЕСКОЕ ДОСЬЕ", font=get_font(13, bold=True), fill=ACCENT_COLOR)
    draw.text((PADDING, 36), title[:65], font=f_title, fill=TEXT_MAIN)

    # Status badge on the right
    conf_text = f"★ {confidence[:36]}"
    badge_color = SUCCESS_COLOR if "VERIFIED" in confidence else ACCENT_COLOR
    draw.rectangle([CANVAS_WIDTH - PADDING - 420, 24, CANVAS_WIDTH - PADDING, 62], fill=CARD_BG, outline=badge_color, width=2)
    draw.text((CANVAS_WIDTH - PADDING - 405, 32), conf_text, font=get_font(16, bold=True), fill=badge_color)

    # 2. Photos Row (Main photo on Left, Satellite/Evidence on Right)
    y_photos = HEADER_HEIGHT + PADDING

    # Left Image Box
    draw.rectangle([PADDING, y_photos, PADDING + card_width, y_photos + row_height], fill=CARD_BG, outline=BORDER_COLOR, width=1)
    if main_photo_path and main_photo_path.exists():
        try:
            with Image.open(main_photo_path) as im:
                im = im.convert("RGB")
                im.thumbnail((card_width - 16, row_height - 50))
                px = PADDING + (card_width - im.width) // 2
                py = y_photos + 36 + (row_height - 50 - im.height) // 2
                canvas.paste(im, (px, py))
        except Exception:
            pass
    draw.text((PADDING + 16, y_photos + 10), "📷 ИСХОДНОЕ ИЗОБРАЖЕНИЕ (СНИМОК С КАМЕРЫ)", font=get_font(13, bold=True), fill=ACCENT_COLOR)

    # Right Image Box (Satellite Orthophoto or Match)
    right_x = PADDING + card_width + PADDING
    draw.rectangle([right_x, y_photos, right_x + card_width, y_photos + row_height], fill=CARD_BG, outline=BORDER_COLOR, width=1)
    sat_used = sat_photo_path or ev_photo_path
    if sat_used and sat_used.exists():
        try:
            with Image.open(sat_used) as im:
                im = im.convert("RGB")
                im.thumbnail((card_width - 16, row_height - 50))
                px = right_x + (card_width - im.width) // 2
                py = y_photos + 36 + (row_height - 50 - im.height) // 2
                canvas.paste(im, (px, py))
        except Exception:
            pass
    label_right = "🛰️ ВЕРИФИКАЦИЯ: СПУТНИКОВЫЙ ОРТОФОТОПЛАН (ZOOM 18)" if sat_photo_path else "🔄 ВЕРИФИКАЦИЯ: AI CROSS-MATCH ПОИСК"
    draw.text((right_x + 16, y_photos + 10), label_right, font=get_font(13, bold=True), fill=SUCCESS_COLOR)

    # 3. Information & OSINT Clues Box
    y_info = y_photos + row_height + PADDING
    draw.rectangle([PADDING, y_info, CANVAS_WIDTH - PADDING, y_info + info_box_height], fill=CARD_BG, outline=BORDER_COLOR, width=1)

    # Header inside info box
    draw.text((PADDING + 20, y_info + 16), "🧭 ГЕОГРАФИЧЕСКАЯ ПРИВЯЗКА И ЦЕЛЕВЫЕ КООРДИНАТЫ", font=f_heading, fill=ACCENT_COLOR)
    coords_str = f"GPS: {lat:.6f}, {lon:.6f}   |   Регион: {region}   |   Объект: {target_name}"
    draw.text((PADDING + 20, y_info + 48), coords_str, font=f_mono, fill=TEXT_MAIN)

    # Description lines
    cur_y = y_info + 82
    draw.text((PADDING + 20, cur_y), "ОБОСНОВАНИЕ:", font=get_font(14, bold=True), fill=TEXT_MUTED)
    cur_y += 24
    for line in desc_lines:
        draw.text((PADDING + 20, cur_y), line, font=f_body, fill=TEXT_MAIN)
        cur_y += 22

    cur_y += 10
    draw.line([(PADDING + 20, cur_y), (CANVAS_WIDTH - PADDING - 20, cur_y)], fill=BORDER_COLOR, width=1)
    cur_y += 14
    draw.text((PADDING + 20, cur_y), "ВЕРИФИЦИРОВАННЫЕ УЛИКИ И ФАКТЫ:", font=get_font(14, bold=True), fill=TEXT_MUTED)
    cur_y += 24
    for cl in clues[:6]:
        wrapped_clues = wrap_text(f"✔  {cl}", f_body, content_width - 60)
        for w_cl in wrapped_clues:
            draw.text((PADDING + 20, cur_y), w_cl, font=f_body, fill=TEXT_MAIN)
            cur_y += 22

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, format="JPEG", quality=92)
    return out_path
