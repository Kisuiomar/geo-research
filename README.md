# 🛰️ GeoSleuth & Geo-Research Framework

> **Advanced OSINT Geolocation, Visual Reconnaissance & Geospatial Analysis Platform**

Geo-Research is an open intelligence suite for automated and interactive visual geolocation of photography, satellite alignment, and geospatial verification. It unifies multi-engine reverse visual searches, astronomical sun/shadow telemetry, national gazetteers, and high-precision building/POI matching.

---

## 🌟 Key Capabilities

### 1. 🔍 Multi-Engine Visual Radar
- **Google Lens & Yandex Vision:** Headless browser automation and API extraction for landmark identification and scene recognition.
- **Ensemble Consensus:** Cross-engine agreement metrics for candidate locations.
- **Crop Candidate Analysis:** Visual zooming and sub-region matching for signs, minarets, towers, and horizon silhouettes.

### 2. ☀️ Astronomical Shadow & Solar Bearing
- **Solar Azimuth & Elevation:** Calculates precise sun vector using photo capture timestamp (EXIF) and candidate GPS coordinates.
- **Shadow Direction Inversion:** Computes camera bearing (heading angle) relative to target landmarks from ground cast shadows.
- **Horizon & Mountain Cascades:** Elevation line-of-sight analysis (e.g. Zailiyskiy Alatau southern horizon filter for Almaty).

### 3. 🗺️ Satellite Orthomosaics & Wayback Tiles
- **High-Resolution Tile Fetcher:** Zoom 17–19 satellite imagery stitching (Google Satellite & Esri).
- **Historical Comparison (Wayback):** Timeline diffing against historical satellite layers to identify construction, demolition, or landscape alterations.

### 4. 📚 National Knowledge Gazetteers (Kazakhstan & Central Asia)
- **Regional License Plate Codes:** All 20 regions and cities of republican significance (01 Ast, 02 Alm, 03 Akl, ..., 20 Jet).
- **Phone Prefix Gazetteer:** Landline and mobile code mappings across oblasts and districts.
- **Architectural & Landmark Database:** Curated high-probability POIs, historical monuments, mosques, and administrative hubs.

### 5. 📷 FindMyPhoto & Forensics
- **EXIF GPS Injection:** Injects verified coordinates and altitude metadata directly into image EXIF headers for export.
- **Error Level Analysis (ELA):** Detects digital image manipulation, cloned regions, and spliced elements.
- **Automated Dossier Generator:** Produces structured Markdown / PDF-ready intelligence dossiers with verified coordinates, confidence scoring, and visual evidence sheets.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- `pip` or `uv`
- Google Chrome or Chromium (for Playwright reverse image scrapers)

### Installation
```bash
# Clone the repository
git clone https://github.com/Kisuiomar/geo-research.git
cd geo-research

# Install dependencies
pip install fastapi uvicorn pillow pydantic requests playwright
playwright install chromium
```

### Launching Web Interface
```bash
python web/server.py
```
Open **[http://127.0.0.1:8765](http://127.0.0.1:8765)** in your browser.

---

## 📁 Repository Structure

```
geo-research/
├── web/
│   ├── server.py              # FastAPI backend application & API routes
│   ├── modules/               # Geolocation modules (solar, phone, plates, wayback, etc.)
│   └── static/                # Single Page Application (HTML5, Vanilla CSS, JS)
│       ├── cases.json         # Case management & intelligence evidence database
│       └── uploads/           # Reference photos, satellite crops, evidence sheets
├── scripts/
│   └── google_lens.py         # Google Lens automation engine
├── geo-sleuth/                # Core geolocation intelligence skills and tile scripts
├── scratch/                   # Test suites and diagnostic utilities
├── query_kz.py                # Regional Kazakhstan geospatial queries
├── query_osm.py               # OpenStreetMap Overpass query helper
├── test_pipeline.py           # End-to-end geolocation pipeline test
└── audit_downloaded_dossier.md# Sample OSINT investigation report
```

---

## 📜 License
MIT License. Developed for research and educational OSINT investigations.
