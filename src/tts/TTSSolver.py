import os

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from TTS.api import TTS


class TTSSolver:
    def __init__(self, model, mode, target_voice_path):
        print("[TTS] 正在初始化神经网络。")
        self.model = model
        self.target_voice_path = target_voice_path
        self.tts = TTS(model_name=model, progress_bar=False).to(mode)

    def get_voice(self, text):
        # return self.model.voice(text)
        return

    def get_file(self, text: str, path):
        if text == "":
            return
        print("[TTS] 正在合成语音。")

        if len(text.split(" ")) <= 2:
            text = text + " " + text

        self.tts.tts_to_file(
            text=text,
            speaker_wav=self.target_voice_path,
            language="en",
            file_path=path,
        )
        return
