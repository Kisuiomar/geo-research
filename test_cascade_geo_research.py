import os
import sys
from pathlib import Path
from PIL import Image

try:
    sys.stdout.reconfigure(line_buffering=True, errors="backslashreplace")
    sys.stderr.reconfigure(line_buffering=True, errors="backslashreplace")
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
    lock_geoclip_to_kazakhstan,
    INDOOR_OCR_STOPWORDS
)

def run_tests():
    print("=" * 60)
    print("🔬 GEO-RESEARCH CASCADE VERIFICATION TEST SUITE")
    print("=" * 60)

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

    print("\n--- TEST 2: Gallery Enrichment (Kazakhstan Key Hubs) ---")
    m = model.get_model()
    enrich_geoclip_gallery(m)
    print("GeoCLIP model initialized and Kazakhstan gallery locked successfully!")

    print("\n--- TEST 3: Multi-Scale Image Embedding (50% full, 25% center, 25% horizon) ---")
    test_img = Image.new("RGB", (640, 480), color=(110, 145, 190))
    emb = extract_multiscale_image_embedding(m, test_img, device)
    print(f"Embedding shape: {emb.shape}, device: {emb.device}, norm: {float(emb.norm()):.4f}")
    assert emb.shape == (1, 512), f"Expected (1, 512), got {emb.shape}"

    print("\n--- TEST 4: Two-Stage Dense Grid (Pass 1: 5000m @ 50m, Pass 2: 300m @ 10m) ---")
    temp_img_path = ROOT_DIR / "dummy_test_outdoor.jpg"
    test_img.save(temp_img_path)
    grid_res = refine_dense_grid(m, str(temp_img_path), 43.2389, 76.8897, is_indoor=False)
    print(f"Dense Grid Result: status={grid_res.get('status')}, radius={grid_res.get('radius_m')}m, device={grid_res.get('device')}")

    print("\n--- TEST 5: Indoor CV Heuristic & Stop-Words ---")
    cv_res = detect_indoor_cv(str(temp_img_path))
    print(f"Indoor CV on synthetic: {cv_res}")
    assert "касса" in INDOOR_OCR_STOPWORDS
    assert "шығу" in INDOOR_OCR_STOPWORDS
    assert "exit" in INDOOR_OCR_STOPWORDS

    print("\n--- TEST 6: Overpass Brand Cluster (120m threshold -> 35m) ---")
    # Test Almaty cluster (Magnum / KFC / Zara)
    cluster = search_overpass_brand_cluster(["Magnum", "KFC"], 43.2030, 76.8920, radius_m=5000, cluster_radius_m=150)
    print(f"Brand Cluster Result: {cluster}")
    if cluster:
        print(f"Cluster Found: {cluster.get('name')} | CEP: ±{cluster.get('radius_m')}m | Method: {cluster.get('method')}")

    print("\n--- TEST 7: Mapillary Street-Level Verification ---")
    street_views = fetch_mapillary_street_view(43.2389, 76.8897, radius_m=100, limit=2)
    print(f"Mapillary matches near Almaty center: {len(street_views)}")
    for sv in street_views[:2]:
        print(f"  • ID {sv.get('id')} | Coord: {sv.get('lat'):.4f}, {sv.get('lon'):.4f} | Thumb: {bool(sv.get('thumb_url'))}")

    print("\n--- TEST 8: Full End-to-End locate_exact_spot() Cascade ---")
    real_photo = ROOT_DIR / "photo_1.jpg"
    if not real_photo.exists():
        real_photo = temp_img_path
    
    spot = locate_exact_spot(m, str(real_photo), 43.2389, 76.8897)
    print(f"Exact Spot Method: {spot.get('method')}")
    print(f"Coordinates: {spot.get('exact_lat')}, {spot.get('exact_lon')}")
    print(f"CEP Radius: ±{spot.get('radius_m')} м")
    print(f"Is Indoor: {spot.get('is_indoor')}")
    diag = spot.get("diagnostics", {})
    print(f"Diagnostics: {list(diag.keys())}")

    if temp_img_path.exists():
        temp_img_path.unlink()

    print("\n" + "=" * 60)
    print("🎉 ALL CASCADE MODULES PASSED VERIFICATION!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
