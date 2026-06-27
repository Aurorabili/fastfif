import os
import sys
import time
import subprocess
import threading
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config as app_config


class TTSInstance:
    def __init__(self, port, use_gpu=True, api_script=None):
        self.port = port
        self.use_gpu = use_gpu
        self.api_script = api_script or app_config.get_api_script()
        self.process = None
        self.working_dir = os.path.dirname(self.api_script)
        self.base_url = f"http://127.0.0.1:{port}"

    def start(self):
        if not os.path.exists(self.api_script):
            print(f"[TTSManager] API脚本不存在: {self.api_script}")
            return False

        env = os.environ.copy()
        if self.use_gpu:
            env["CUDA_VISIBLE_DEVICES"] = "0"
        else:
            env["CUDA_VISIBLE_DEVICES"] = "-1"
            env["FORCE_CPU"] = "1"

        cmd = [sys.executable, self.api_script, "--port", str(self.port)]
        print(f"[TTSManager] 启动TTS实例: 端口={self.port}, GPU={self.use_gpu}")
        print(f"[TTSManager] 命令: {' '.join(cmd)}")

        self.process = subprocess.Popen(
            cmd,
            stdout=None,
            stderr=None,
            cwd=self.working_dir,
            env=env,
        )

        time.sleep(8)

        if self.process.poll() is not None:
            print(
                f"[TTSManager] TTS实例启动失败(端口{self.port}), 返回码: {self.process.poll()}"
            )
            return False

        for attempt in range(10):
            try:
                resp = requests.get(f"{self.base_url}/docs", timeout=2)
                if resp.status_code == 200:
                    print(f"[TTSManager] TTS实例已就绪(端口{self.port})")
                    return True
            except Exception:
                pass
            time.sleep(3)

        if self.process.poll() is not None:
            print(f"[TTSManager] TTS实例在启动过程中崩溃(端口{self.port})")
            return False

        print(f"[TTSManager] TTS实例可能未就绪但进程存活(端口{self.port})")
        return True

    def stop(self):
        if self.process and self.process.poll() is None:
            print(f"[TTSManager] 正在停止TTS实例(端口{self.port})...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            print(f"[TTSManager] TTS实例已停止(端口{self.port})")

    def is_alive(self):
        return self.process is not None and self.process.poll() is None

    def synthesize(self, text, prompt_audio_path, output_path, infer_mode="普通推理"):
        files = {"prompt_audio": open(prompt_audio_path, "rb")}
        data = {
            "text": text,
            "infer_mode": infer_mode,
        }
        try:
            response = requests.post(
                f"{self.base_url}/tts", files=files, data=data, timeout=300
            )
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return True
            else:
                print(
                    f"[TTSManager] TTS请求失败(端口{self.port}), 状态码: {response.status_code}"
                )
                return False
        except Exception as e:
            print(f"[TTSManager] TTS请求异常(端口{self.port}): {str(e)}")
            return False
        finally:
            try:
                if not files["prompt_audio"].closed:
                    files["prompt_audio"].close()
            except Exception:
                pass


class TTSManager:
    def __init__(self, config):
        self.config = config
        self.instances = []
        self.gpu_instances = []
        self.cpu_instances = []
        self.inference_semaphore = None
        self.request_lock = threading.Lock()
        self._started = False

        schedule_mode = config.get("schedule_mode", "priority_pipeline")
        max_gpu = config.get("max_gpu_instances", 1)
        max_cpu = config.get("max_cpu_instances", 0)

        gpu_ports = config.get("gpu_ports", [])
        cpu_ports = config.get("cpu_ports", [])

        for i in range(max_gpu):
            port = gpu_ports[i] if i < len(gpu_ports) else 6008 + i
            inst = TTSInstance(port=port, use_gpu=True)
            self.gpu_instances.append(inst)
            self.instances.append(inst)

        for i in range(max_cpu):
            port = cpu_ports[i] if i < len(cpu_ports) else 7008 + i
            inst = TTSInstance(port=port, use_gpu=False)
            self.cpu_instances.append(inst)
            self.instances.append(inst)

        if schedule_mode == "multi_gpu_locked":
            self.inference_semaphore = threading.Semaphore(1)
        elif schedule_mode == "priority_pipeline":
            self.inference_semaphore = threading.Semaphore(1)
        elif schedule_mode == "gpu_cpu_hybrid":
            self.inference_semaphore = threading.Semaphore(max_gpu)
            for _ in range(max_cpu):
                pass
        else:
            self.inference_semaphore = threading.Semaphore(1)

    def start(self):
        if self._started:
            return True

        print(
            f"[TTSManager] 正在启动 {len(self.gpu_instances)} 个GPU实例, {len(self.cpu_instances)} 个CPU实例..."
        )

        for inst in self.instances:
            success = inst.start()
            if not success:
                print(f"[TTSManager] 实例启动失败(端口{inst.port})，尝试继续...")

        self._started = True
        return True

    def stop(self):
        print("[TTSManager] 正在停止所有TTS实例...")
        for inst in self.instances:
            inst.stop()
        self._started = False

    def get_gpu_instance(self, account_index=0):
        if not self.gpu_instances:
            return None
        idx = account_index % len(self.gpu_instances)
        return self.gpu_instances[idx]

    def get_cpu_instance(self):
        if not self.cpu_instances:
            return None
        return self.cpu_instances[0]

    def get_instance_for_account(self, account_index=0):
        schedule_mode = self.config.get("schedule_mode", "priority_pipeline")
        if schedule_mode == "multi_gpu_locked":
            return self.get_gpu_instance(account_index)
        return self.get_gpu_instance(0)

    def synthesize_with_semaphore(
        self,
        text,
        prompt_audio_path,
        output_path,
        priority=1,
        prefer_cpu=False,
        infer_mode="普通推理",
    ):
        schedule_mode = self.config.get("schedule_mode", "priority_pipeline")
        cpu_threshold = self.config.get("cpu_text_length_threshold", 15)

        target_instance = self.get_gpu_instance(0)

        if schedule_mode == "gpu_cpu_hybrid" and self.cpu_instances:
            word_count = len(text.split())
            if prefer_cpu or (word_count <= cpu_threshold and priority > 1):
                cpu_inst = self.get_cpu_instance()
                if cpu_inst and cpu_inst.is_alive():
                    target_instance = cpu_inst

        if target_instance is None:
            target_instance = self.gpu_instances[0] if self.gpu_instances else None
        if target_instance is None:
            print("[TTSManager] 没有可用的TTS实例!")
            return False

        print(
            f"[TTSManager] 请求TTS: 端口={target_instance.port}, 优先级={priority}, GPU={target_instance.use_gpu}"
        )

        self.inference_semaphore.acquire()
        try:
            return target_instance.synthesize(
                text, prompt_audio_path, output_path, infer_mode
            )
        finally:
            self.inference_semaphore.release()
