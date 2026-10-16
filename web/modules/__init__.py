"""GeoSleuth Advanced Geolocation and Forensic Modules.

Integrated from:
- GeoLens
- Geo-Guesser
- Searching-skill
- Ubinam
- FindMyPhoto
- SpyBrain
"""
from web.modules.driving_side import analyze_driving_side, LEFT_DRIVE_COUNTRIES
from web.modules.phone_lookup import lookup_phone_number, extract_phone_candidates
from web.modules.knowledge_rules import evaluate_photo_clues, analyze_license_plates, analyze_script_and_language
from web.modules.wayback import get_releases, fetch_wayback_tile, fetch_wayback_comparison
from web.modules.evidence_sheet import compose_evidence_sheet
from web.modules.sun_shadow import calculate_solar_position, estimate_camera_bearing_from_shadow
from web.modules.geo_utils import (
    haversine_distance, initial_bearing, destination_point,
    wgs84_to_gcj02, gcj02_to_wgs84, gcj02_to_bd09, bd09_to_gcj02, bd09_to_wgs84,
    wgs84_to_bd09
)
from web.modules.temporal_cluster import parse_exif_timestamp, interpolate_from_timeline
from web.modules.kz_engine import (
    KAZAKHSTAN_REGIONS, KAZAKHSTAN_LANDMARKS_GAZETTEER, KZ_KNOWLEDGE_CATEGORIES,
    generate_kz_first_answer, evaluate_ubinam_confidence_ladder,
    mine_kazakh_signboards, validate_kazakh_iin_bin,
    calculate_kz_distance_matrix, inject_gps_exif
)
from web.modules.exact_locator import (
    locate_exact_spot, refine_dense_grid_gpu, refine_dense_grid,
    extract_multiscale_image_embedding, enrich_geoclip_gallery,
    set_geoclip_region, lock_geoclip_to_kazakhstan, detect_indoor_cv,
    search_overpass_brand_cluster, fetch_mapillary_street_view,
    analyze_with_gemini_vision, extract_text_from_photo,
    extract_global_and_kz_clues, extract_kz_metadata_clues,
    geocode_osm_global, get_device,
    preprocess_clean_internet_image, compute_image_dhash,
    verify_and_geocode_landmark, semantic_sanity_check,
    visual_memory, search_ocr_osm, haversine_km,
    INDOOR_OCR_STOPWORDS
)
from web.modules import model
