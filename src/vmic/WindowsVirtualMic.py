import sounddevice as sd
import soundfile as sf


class WindowsVirtualMic:

    def __init__(self, device_name=None):
        if device_name:
            self.device_name = device_name
        else:
            self.device_name = "CABLE Input (VB-Audio Virtual Cable)"
        self.device_index = self.find_device_index()

    def find_device_index(self):
        """查找音频输出设备的索引"""
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if self.device_name in dev["name"] and dev["max_output_channels"] > 0:
                return i
        print(
            f"[WindowsVirtualMic] 警告: 未找到设备 '{self.device_name}'，使用默认输出设备"
        )
        return None

    def play(self, file_path):
        """使用 sounddevice 播放音频到指定设备"""
        print(
            f"[WindowsVirtualMic] 音频流开始从 {file_path} 播放到虚拟声卡：{self.device_name}"
        )

        try:
            data, fs = sf.read(file_path, dtype="float32")

            sd.play(data, fs, device=self.device_index)
            sd.wait()

            print(f"[WindowsVirtualMic] 播放成功")
        except Exception as e:
            print(f"[WindowsVirtualMic] 播放失败: {e}")

        print("[WindowsVirtualMic] 音频流结束")
