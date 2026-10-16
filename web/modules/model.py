import gc
import logging
import os
import threading
import time
from io import BytesIO
from typing import List, Dict, Any, Optional

try:
    import torch
except ImportError:
    torch = None

logger = logging.getLogger(__name__)

_model = None
_loaded = False
_lock = threading.Lock()
_last_used = 0.0

def is_loaded() -> bool:
    return _loaded

def get_model():
    """Возвращает загруженный инстанс GeoCLIP."""
    _ensure_loaded()
    return _model

def _ensure_loaded() -> None:
    global _model, _loaded, _last_used
    with _lock:
        _last_used = time.time()
        if _loaded and _model is not None:
            return
        logger.info("Loading GeoCLIP model into RAM / GPU...")
        try:
            from geoclip import GeoCLIP

            _model = GeoCLIP()
            if torch is not None and torch.cuda.is_available():
                try:
                    _model = _model.to("cuda")
                    logger.info("GeoCLIP moved to CUDA GPU: %s", torch.cuda.get_device_name(0))
                except Exception as ex:
                    logger.warning("Could not move GeoCLIP to CUDA: %s", ex)

            _loaded = True
            try:
                from web.modules.exact_locator import enrich_geoclip_gallery
                enrich_geoclip_gallery(_model, region_mode="global")
                logger.info("GeoCLIP gallery enriched with worldwide dataset + Kazakhstan hubs")
            except Exception:
                logger.exception("Failed to enrich GeoCLIP gallery on load")
            logger.info("GeoCLIP loaded and ready")
        except Exception:
            logger.exception("Failed to load GeoCLIP")
            _loaded = False
            raise

def unload() -> None:
    global _model, _loaded
    with _lock:
        _model = None
        _loaded = False
        gc.collect()
        if torch is not None and torch.cuda.is_available():
            torch.cuda.empty_cache()
    logger.info("GeoCLIP model unloaded")

def predict(image_bytes_or_path, top_k: int = 5, region_mode: str = "global") -> List[Dict[str, Any]]:
    """Выполняет инференс GeoCLIP для фото, возвращая топ-К предсказаний по всему миру или в режиме KZ."""
    _ensure_loaded()
    if _model is None:
        return []

    try:
        from web.modules.exact_locator import set_geoclip_region
        set_geoclip_region(_model, region_mode=region_mode)
    except Exception:
        pass

    try:
        if isinstance(image_bytes_or_path, (bytes, bytearray)):
            img_input = BytesIO(image_bytes_or_path)
        else:
            img_input = image_bytes_or_path

        top_pred_lat_lon, top_prob = _model.predict(img_input, top_k=top_k)

        results = []
        for (lat, lon), prob in zip(top_pred_lat_lon, top_prob):
            results.append({
                "lat": float(lat),
                "lon": float(lon),
                "probability": float(prob),
                "score": float(prob),
            })
        return results
    except Exception as e:
        logger.exception("Error during GeoCLIP prediction: %s", e)
        return []

