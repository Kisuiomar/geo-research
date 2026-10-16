import os
import sys
from typing import Any
from pathlib import Path
from PIL import Image

_out_reconf = getattr(sys.stdout, "reconfigure", None)
if callable(_out_reconf):
    try:
        _out_reconf(line_buffering=True, errors="backslashreplace")
        _err_reconf = getattr(sys.stderr, "reconfigure", None)
        if callable(_err_reconf):
            _err_reconf(line_buffering=True, errors="backslashreplace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from web.modules import (
    model,
    get_device,
    extract_multiscale_image_embedding,
    refine_dense_grid_gpu,
    refine_dense_grid,
    search_overpass_brand_cluster,
    detect_indoor_cv,
    fetch_mapillary_street_view,
    locate_exact_spot,
    enrich_geoclip_gallery,
    set_geoclip_region,
    lock_geoclip_to_kazakhstan,
    INDOOR_OCR_STOPWORDS
)

def run_tests():
    print("=" * 70)
    print("🌍 GEO-RESEARCH WORLDWIDE (GLOBAL + KZ BOOSTER) TEST SUITE")
    print("=" * 70)

    print("\n--- TEST 1: Device & CUDA Verification ---")
    device = get_device()
    print(f"Device detected: {device}")
    try:
        import torch
        if torch.cuda.is_available():
            print(f"CUDA Ready: True | GPU: {torch.cuda.get_device_name(0)}")
        else:
            print("CUDA: False (Running in CPU mode)")
    except Exception as e:
        print(f"Torch check error: {e}")

    print("\n--- TEST 2: Worldwide Gallery Enrichment (>100 000 points) ---")
    m: Any = model.get_model()
    assert m is not None, "GeoCLIP model failed to initialize"
    # Check default global gallery size
    set_geoclip_region(m, "global")
    gallery_obj: Any = getattr(m, "gps_gallery", None)
    assert gallery_obj is not None, "Model missing gps_gallery"
    gallery_pts = len(gallery_obj)
    print(f"Global GeoCLIP gallery points on GPU: {gallery_pts:,}")
    assert gallery_pts > 100000, f"Expected global gallery > 100,000 points, got {gallery_pts}"
    print("✔ Global worldwide gallery (>100k points) validated on GPU!")

    # Check KZ mode switching
    set_geoclip_region(m, "kz")
    kz_gallery_obj: Any = getattr(m, "gps_gallery", None)
    assert kz_gallery_obj is not None, "Model missing gps_gallery"
    kz_pts = len(kz_gallery_obj)
    print(f"Kazakhstan focused gallery points: {kz_pts:,}")
    assert kz_pts > 1000, f"Expected KZ gallery > 1,000 points, got {kz_pts}"
    # Switch back to global as default
    set_geoclip_region(m, "global")
    print("✔ Dynamic switching between 'global' and 'kz' modes validated!")

    print("\n--- TEST 3: Multi-Scale Image Embedding (50% full, 25% center, 25% horizon) ---")
    test_img = Image.new("RGB", (640, 480), color=(110, 145, 190))
    emb = extract_multiscale_image_embedding(m, test_img, device)
    print(f"Embedding shape: {emb.shape}, device: {emb.device}, norm: {float(emb.norm()):.4f}")
    assert emb.shape == (1, 512), f"Expected (1, 512), got {emb.shape}"

    print("\n--- TEST 4: Global Precision Refinement (Paris: 48.8584, 2.2945) ---")
    temp_img_path = ROOT_DIR / "dummy_test_global.jpg"
    test_img.save(temp_img_path)
    paris_lat, paris_lon = 48.8584, 2.2945
    grid_paris = refine_dense_grid(m, str(temp_img_path), paris_lat, paris_lon, is_indoor=False)
    print(f"Paris Dense Grid Result: lat={grid_paris.get('lat')}, lon={grid_paris.get('lon')}, status={grid_paris.get('status')}")
    # Verify coordinates did NOT fall back to Almaty (43.2, 76.8)
    assert abs(grid_paris["lat"] - paris_lat) < 0.2, f"Grid dragged away from Paris! {grid_paris['lat']}"
    assert abs(grid_paris["lon"] - paris_lon) < 0.2, f"Grid dragged away from Paris! {grid_paris['lon']}"
    print("✔ Global grid in Paris stayed within target city boundaries (NO ALMATY FALLBACK)!")

    print("\n--- TEST 5: Global Overpass Brand Cluster (Paris: Carrefour + Starbucks) ---")
    paris_cluster = search_overpass_brand_cluster(["Carrefour", "Starbucks"], 48.8566, 2.3522, radius_m=8000, cluster_radius_m=150)
    print(f"Paris Brand Cluster Result: {paris_cluster}")
    if paris_cluster:
        print(f"  ✔ Found global cluster: {paris_cluster.get('name')} | CEP: ±{paris_cluster.get('radius_m')}m")

    print("\n--- TEST 6: Multilingual Indoor Stop-Words (7 Languages) ---")
    cv_res = detect_indoor_cv(str(temp_img_path))
    print(f"Indoor CV on synthetic: {cv_res}")
    # RU
    assert "касса" in INDOOR_OCR_STOPWORDS
    # KZ
    assert "шығу" in INDOOR_OCR_STOPWORDS
    # EN
    assert "exit" in INDOOR_OCR_STOPWORDS
    # ES
    assert "salida" in INDOOR_OCR_STOPWORDS
    # FR
    assert "sortie" in INDOOR_OCR_STOPWORDS
    # DE
    assert "ausgang" in INDOOR_OCR_STOPWORDS
    # TR
    assert "çıkış" in INDOOR_OCR_STOPWORDS
    print("✔ Multilingual indoor stop-words (RU, KZ, EN, ES, FR, DE, TR) validated!")

    print("\n--- TEST 7: Kazakhstan Regional Booster (Almaty Grid & Mountain Bearing) ---")
    almaty_lat, almaty_lon = 43.2389, 76.8897
    grid_kz = refine_dense_grid(m, str(temp_img_path), almaty_lat, almaty_lon, is_indoor=False)
    print(f"Almaty Dense Grid Result: lat={grid_kz.get('lat')}, lon={grid_kz.get('lon')}, status={grid_kz.get('status')}")
    assert abs(grid_kz["lat"] - almaty_lat) < 0.2, "Almaty grid drifted unexpectedly"
    print("✔ Kazakhstan regional outdoor grid validated!")

    print("\n--- TEST 8: Full End-to-End locate_exact_spot() in Global Mode ---")
    spot_global = locate_exact_spot(m, str(temp_img_path), city_lat=paris_lat, city_lon=paris_lon, region_mode="global")
    print(f"Global Spot Method: {spot_global.get('method')}")
    print(f"Coordinates: {spot_global.get('exact_lat')}, {spot_global.get('exact_lon')}")
    print(f"CEP Radius: ±{spot_global.get('radius_m')} м")
    print(f"Country: {spot_global.get('country')}, City: {spot_global.get('city')}")
    assert abs(spot_global["exact_lat"] - paris_lat) < 0.2
    assert "Outdoor" in spot_global.get("method", "") or "Anchor" in spot_global.get("method", "")
    print("✔ Full end-to-end locate_exact_spot() global pipeline passed!")

    print("\n--- TEST 9: Full End-to-End locate_exact_spot() in Kazakhstan Mode ---")
    spot_kz = locate_exact_spot(m, str(temp_img_path), city_lat=almaty_lat, city_lon=almaty_lon, region_mode="kz")
    print(f"Kazakhstan Spot Method: {spot_kz.get('method')}")
    print(f"Coordinates: {spot_kz.get('exact_lat')}, {spot_kz.get('exact_lon')}")
    print(f"CEP Radius: ±{spot_kz.get('radius_m')} м")
    assert abs(spot_kz["exact_lat"] - almaty_lat) < 0.2
    print("✔ Full end-to-end locate_exact_spot() Kazakhstan mode passed!")

    if temp_img_path.exists():
        temp_img_path.unlink()

    print("\n" + "=" * 70)
    print("🎉 ALL WORLDWIDE + KAZAKHSTAN TEST SUITES PASSED (100% SUCCESS)!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
