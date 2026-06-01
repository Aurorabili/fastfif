# 修改后的 TTSSolver 类（文档2）
import requests
import os
import random


class TTSSolver:
    def __init__(self, model, mode, target_voice_path, drop_level=0.2, complexity=5):
        print("[TTS] 正在初始化IndexTTS神经网络。")
        self.model = model
        self.target_voice_path = target_voice_path
        self.drop_level = drop_level  # 单词丢弃程度 (0-1)
        self.complexity = complexity  # 长难单词复杂度 (最小字符数)
        self.api_url = "http://127.0.0.1:6008/tts"

    def get_voice(self, text):
        return

    def process_text(self, text):
        """处理文本，随机丢弃长难单词"""
        original_text = text
        words = text.split()

        # 过滤出长难单词（长度大于等于复杂度的单词）
        complex_words = [word for word in words if len(word) >= self.complexity]

        # 随机丢弃一部分长难单词
        if complex_words and self.drop_level > 0:
            # 计算要丢弃的单词数量
            drop_count = max(1, int(len(complex_words) * self.drop_level))

            # 随机选择要丢弃的单词
            words_to_drop = random.sample(
                complex_words, min(drop_count, len(complex_words))
            )

            # 从原文本中移除选中的单词
            processed_words = [word for word in words if word not in words_to_drop]

            # 重新组合文本
            processed_text = " ".join(processed_words)

            print(f"[TTS] 原答案: {original_text}")
            print(f"[TTS] 处理后答案: {processed_text}")
            print(f"[TTS] 丢弃了 {len(words_to_drop)} 个长难单词")

            return processed_text

        return text

    def get_file(self, text: str, path):
        if text == "":
            return
        print("[TTS] 正在通过IndexTTS合成语音。")

        # 处理文本，随机丢弃长难单词
        processed_text = self.process_text(text)

        # 保留原逻辑：短文本重复一次
        if len(processed_text.split(" ")) <= 2:
            processed_text = processed_text + " " + processed_text

        try:
            files = {"prompt_audio": open(self.target_voice_path, "rb")}
            data = {
                "text": processed_text,
                "infer_mode": "普通推理",
            }

            response = requests.post(self.api_url, files=files, data=data)

            if response.status_code == 200:
                with open(path, "wb") as f:
                    f.write(response.content)
                print("[TTS] 语音合成成功。")
            else:
                print(f"[TTS] 语音合成失败，状态码: {response.status_code}")

        except Exception as e:
            print(f"[TTS] 调用IndexTTS API时出错: {str(e)}")
        finally:
            if "prompt_audio" in locals() and not files["prompt_audio"].closed:
                files["prompt_audio"].close()

        return
