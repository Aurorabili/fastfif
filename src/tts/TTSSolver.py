import requests
import os
import json
import time
import random


class GpuBusyFlag:
    _FLAG_DIR = os.path.join(os.getcwd(), "tmp")
    _FLAG_FILE = os.path.join(_FLAG_DIR, "gpu_status.flag")
    _STALE_TIMEOUT = 180

    @classmethod
    def _ensure_dir(cls):
        os.makedirs(cls._FLAG_DIR, exist_ok=True)

    @classmethod
    def mark_busy(cls, is_long_inference=False):
        cls._ensure_dir()
        try:
            data = {
                "pid": os.getpid(),
                "start_time": time.time(),
                "is_long": is_long_inference,
            }
            with open(cls._FLAG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    @classmethod
    def mark_idle(cls):
        try:
            if os.path.exists(cls._FLAG_FILE):
                os.remove(cls._FLAG_FILE)
        except Exception:
            pass

    @classmethod
    def is_gpu_busy_with_long(cls):
        if not os.path.exists(cls._FLAG_FILE):
            return False
        try:
            with open(cls._FLAG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            elapsed = time.time() - data.get("start_time", 0)
            if elapsed > cls._STALE_TIMEOUT:
                try:
                    os.remove(cls._FLAG_FILE)
                except Exception:
                    pass
                return False
            return data.get("is_long", False)
        except Exception:
            try:
                os.remove(cls._FLAG_FILE)
            except Exception:
                pass
            return False


class TTSSolver:
    def __init__(
        self,
        model,
        mode,
        target_voice_path,
        drop_level=0.2,
        complexity=5,
        api_url=None,
        api_url_cpu=None,
        tts_manager=None,
        account_priority=1,
        cpu_text_threshold=15,
    ):
        print("[TTS] 正在初始化IndexTTS神经网络。")
        self.model = model
        self.target_voice_path = target_voice_path
        self.drop_level = drop_level
        self.complexity = complexity
        self.api_url = api_url or "http://127.0.0.1:6008/tts"
        self.api_url_cpu = api_url_cpu
        self.tts_manager = tts_manager
        self.account_priority = account_priority
        self.cpu_text_threshold = cpu_text_threshold

    def get_voice(self, text):
        return

    def process_text(self, text):
        original_text = text
        words = text.split()

        complex_words = [word for word in words if len(word) >= self.complexity]

        if complex_words and self.drop_level > 0:
            drop_count = max(1, int(len(complex_words) * self.drop_level))

            words_to_drop = random.sample(
                complex_words, min(drop_count, len(complex_words))
            )

            processed_words = [word for word in words if word not in words_to_drop]

            processed_text = " ".join(processed_words)

            print(f"[TTS] 原答案: {original_text}")
            print(f"[TTS] 处理后答案: {processed_text}")
            print(f"[TTS] 丢弃了 {len(words_to_drop)} 个长难单词")

            return processed_text

        return text

    def _choose_api_url(self, text):
        if self.api_url_cpu is None:
            return self.api_url, "GPU"

        word_count = len(text.split())

        if word_count > self.cpu_text_threshold:
            return self.api_url, "GPU"

        if GpuBusyFlag.is_gpu_busy_with_long():
            return self.api_url_cpu, "CPU"
        else:
            return self.api_url, "GPU"

    def get_file(self, text: str, path):
        if text == "":
            return
        print("[TTS] 正在通过IndexTTS合成语音。")

        processed_text = self.process_text(text)

        if len(processed_text.split(" ")) <= 2:
            processed_text = processed_text + " " + processed_text

        if self.tts_manager:
            self._get_file_via_manager(processed_text, path)
        else:
            self._get_file_direct(processed_text, path)

    def _get_file_via_manager(self, processed_text, path):
        try:
            prefer_cpu = False
            if self.api_url_cpu:
                word_count = len(processed_text.split())
                if word_count <= self.cpu_text_threshold:
                    prefer_cpu = GpuBusyFlag.is_gpu_busy_with_long()

            success = self.tts_manager.synthesize_with_semaphore(
                text=processed_text,
                prompt_audio_path=self.target_voice_path,
                output_path=path,
                priority=self.account_priority,
                prefer_cpu=prefer_cpu,
                infer_mode="普通推理",
            )
            if success:
                print("[TTS] 语音合成成功(通过TTSManager)。")
            else:
                print("[TTS] 语音合成失败(通过TTSManager)，尝试直接调用...")
                self._get_file_direct(processed_text, path)
        except Exception as e:
            print(f"[TTS] 通过TTSManager合成时出错: {str(e)}，尝试直接调用...")
            self._get_file_direct(processed_text, path)

    def _get_file_direct(self, processed_text, path):
        target_url, device_type = self._choose_api_url(processed_text)
        word_count = len(processed_text.split())
        is_long = word_count > self.cpu_text_threshold

        if device_type == "GPU":
            GpuBusyFlag.mark_busy(is_long_inference=is_long)

        print(
            f"[TTS] 路由到{device_type}实例 (词数={word_count}, "
            f"{'长文本' if is_long else '短文本'}, "
            f"GPU忙于长推理={GpuBusyFlag.is_gpu_busy_with_long()})"
        )

        try:
            files = {"prompt_audio": open(self.target_voice_path, "rb")}
            data = {
                "text": processed_text,
                "infer_mode": "普通推理",
            }

            response = requests.post(target_url, files=files, data=data, timeout=300)

            if response.status_code == 200:
                with open(path, "wb") as f:
                    f.write(response.content)
                print(f"[TTS] 语音合成成功({device_type})。")
            else:
                if device_type == "CPU" and self.api_url != target_url:
                    print(
                        f"[TTS] CPU实例合成失败(状态码: {response.status_code})，回退到GPU..."
                    )
                    self._fallback_to_gpu(processed_text, path)
                else:
                    print(f"[TTS] 语音合成失败，状态码: {response.status_code}")

        except requests.exceptions.Timeout:
            if device_type == "CPU" and self.api_url != target_url:
                print(f"[TTS] CPU实例超时，回退到GPU...")
                self._fallback_to_gpu(processed_text, path)
            else:
                print(f"[TTS] 调用IndexTTS API超时: {target_url}")

        except Exception as e:
            if device_type == "CPU" and self.api_url != target_url:
                print(f"[TTS] CPU实例出错({str(e)})，回退到GPU...")
                self._fallback_to_gpu(processed_text, path)
            else:
                print(f"[TTS] 调用IndexTTS API时出错: {str(e)}")

        finally:
            if device_type == "GPU":
                GpuBusyFlag.mark_idle()
            if (
                "files" in locals()
                and "prompt_audio" in files
                and not files["prompt_audio"].closed
            ):
                files["prompt_audio"].close()

    def _fallback_to_gpu(self, processed_text, path):
        GpuBusyFlag.mark_busy(is_long_inference=False)
        try:
            files = {"prompt_audio": open(self.target_voice_path, "rb")}
            data = {
                "text": processed_text,
                "infer_mode": "普通推理",
            }

            response = requests.post(self.api_url, files=files, data=data, timeout=300)

            if response.status_code == 200:
                with open(path, "wb") as f:
                    f.write(response.content)
                print("[TTS] GPU回退合成成功。")
            else:
                print(f"[TTS] GPU回退合成失败，状态码: {response.status_code}")

        except Exception as e:
            print(f"[TTS] GPU回退也失败: {str(e)}")

        finally:
            GpuBusyFlag.mark_idle()
            if (
                "files" in locals()
                and "prompt_audio" in files
                and not files["prompt_audio"].closed
            ):
                files["prompt_audio"].close()
