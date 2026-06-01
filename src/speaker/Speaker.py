# 修改后的 Speaker 类（文档3）
import time, os
import platform
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
    ):
        # 使用IndexTTS替代原TTS，添加丢弃程度和复杂度参数
        self.tts_solver = TTSSolver(
            tts_model_name, mode, target_voice_path, drop_level, complexity
        )

        # 根据平台选择虚拟麦克风实现
        if platform.system() == "Linux":
            from vmic.VirtualMic import VirtualMic

            self.virtual_mic = VirtualMic(vmic, "s16le", "44100", "2")
        elif platform.system() == "Windows":
            from vmic.WindowsVirtualMic import WindowsVirtualMic

            self.virtual_mic = WindowsVirtualMic()
        else:
            raise NotImplementedError("Unsupported operating system")

    def set_drop_level(self, drop_level):
        """设置单词丢弃程度"""
        self.tts_solver.drop_level = drop_level
        print(f"[Speaker] 设置单词丢弃程度为: {drop_level}")

    def set_complexity(self, complexity):
        """设置长难单词复杂度"""
        self.tts_solver.complexity = complexity
        print(f"[Speaker] 设置长难单词复杂度为: {complexity}")

    def speak(self, text: str):
        print("[Speaker] 正在合成语音。")
        os.makedirs("tmp", exist_ok=True)
        temp_file = f"tmp/temp_{int(time.time())}.wav"
        self.tts_solver.get_file(text, temp_file)
        print("[Speaker] 正在播放语音。")
        self.virtual_mic.play(temp_file)
        try:
            os.remove(temp_file)
        except:
            pass
        print("[Speaker] 语音播放完成。")
        return
