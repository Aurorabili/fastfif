import os
import json
import time


class MicController:
    _FLAG_DIR = os.path.join(os.getcwd(), "tmp")
    _SPEAKER_FLAG = os.path.join(_FLAG_DIR, "current_speaker.flag")
    _STALE_TIMEOUT = 120

    @classmethod
    def set_speaker(cls, username):
        os.makedirs(cls._FLAG_DIR, exist_ok=True)
        try:
            data = {
                "username": username,
                "start_time": time.time(),
            }
            with open(cls._SPEAKER_FLAG, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    @classmethod
    def clear_speaker(cls):
        try:
            if os.path.exists(cls._SPEAKER_FLAG):
                os.remove(cls._SPEAKER_FLAG)
        except Exception:
            pass

    @classmethod
    def get_speaker(cls):
        if not os.path.exists(cls._SPEAKER_FLAG):
            return None
        try:
            with open(cls._SPEAKER_FLAG, "r", encoding="utf-8") as f:
                data = json.load(f)
            elapsed = time.time() - data.get("start_time", 0)
            if elapsed > cls._STALE_TIMEOUT:
                try:
                    os.remove(cls._SPEAKER_FLAG)
                except Exception:
                    pass
                return None
            return data.get("username")
        except Exception:
            try:
                os.remove(cls._SPEAKER_FLAG)
            except Exception:
                pass
            return None
