import time
import os
import platform
import threading
from tts.TTSSolver import TTSSolver
from vmic.VirtualMic import VirtualMic


class Speaker:
    def __init__(
        self,
        tts_model_name,
        mode,
        vmic,
        target_voice_path,
        drop_level=0.2,
        complexity=5,
        mic_lock=None,
        vmic_device_name=None,
        tts_manager=None,
        tts_api_url=None,
        tts_api_url_cpu=None,
        account_priority=1,
        cpu_text_threshold=15,
        username=None,
    ):
        self.tts_solver = TTSSolver(
            tts_model_name,
            mode,
            target_voice_path,
            drop_level,
            complexity,
            api_url=tts_api_url,
            api_url_cpu=tts_api_url_cpu,
            tts_manager=tts_manager,
            account_priority=account_priority,
            cpu_text_threshold=cpu_text_threshold,
        )

        self.mic_lock = mic_lock
        self.username = username

        if platform.system() == "Linux":
            from vmic.VirtualMic import VirtualMic

            self.virtual_mic = VirtualMic(vmic, "s16le", "44100", "2")
        elif platform.system() == "Windows":
            from vmic.WindowsVirtualMic import WindowsVirtualMic

            self.virtual_mic = WindowsVirtualMic(device_name=vmic_device_name)
        else:
            raise NotImplementedError("Unsupported operating system")

    def set_drop_level(self, drop_level):
        self.tts_solver.drop_level = drop_level
        print(f"[Speaker] 设置单词丢弃程度为: {drop_level}")

    def set_complexity(self, complexity):
        self.tts_solver.complexity = complexity
        print(f"[Speaker] 设置长难单词复杂度为: {complexity}")

    def speak(self, text: str):
        print("[Speaker] 正在合成语音。")
        os.makedirs("tmp", exist_ok=True)
        temp_file = f"tmp/temp_{os.getpid()}_{int(time.time() * 1000)}_{threading.get_ident() % 10000}.wav"
        self.tts_solver.get_file(text, temp_file)
        print("[Speaker] 正在播放语音。")

        if self.mic_lock:
            self.mic_lock.acquire()
            try:
                if self.username:
                    from scheduler.mic_controller import MicController

                    MicController.set_speaker(self.username)
                    time.sleep(0.3)
                self.virtual_mic.play(temp_file)
                if self.username:
                    MicController.clear_speaker()
            finally:
                self.mic_lock.release()
        else:
            if self.username:
                from scheduler.mic_controller import MicController

                MicController.set_speaker(self.username)
                time.sleep(0.3)
            self.virtual_mic.play(temp_file)
            if self.username:
                from scheduler.mic_controller import MicController

                MicController.clear_speaker()

        try:
            os.remove(temp_file)
        except Exception:
            pass
        print("[Speaker] 语音播放完成。")
        return
