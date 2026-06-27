import os
import json

_config_cache = None
_config_path = os.path.join(os.getcwd(), "user.json")


def load_global_config(force_reload=False):
    global _config_cache
    if _config_cache is not None and not force_reload:
        return _config_cache

    if not os.path.exists(_config_path):
        _config_cache = {}
        return _config_cache

    try:
        with open(_config_path, "r", encoding="utf-8") as f:
            _config_cache = json.load(f)
    except Exception:
        _config_cache = {}

    return _config_cache


def get(key, default=None):
    cfg = load_global_config()
    return cfg.get(key, default)


def get_api_script():
    return get(
        "api_script", r"D:\University\More\AI\Echo\index-tts\index-tts\api_server.py"
    )


def get_translation_model_path():
    return get(
        "translation_model_path", r"D:\University\More\translate_model\m2m100_418M"
    )


def get_translation_model_type():
    return get("translation_model_type", "m2m100_418M")


def get_browser_channel():
    return get("browser_channel", "msedge")


def get_viewport():
    vp = get("viewport", [1200, 800])
    return {"width": vp[0], "height": vp[1]}


def get_default_vmic_device():
    return get("default_vmic_device", "CABLE Input (VB-Audio Virtual Cable)")


def get_login_state_expire_days():
    return get("login_state_expire_days", 7)
