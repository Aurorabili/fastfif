import os
import io
import json
import time
import multiprocessing
import traceback
import sys
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config as app_config

try:
    import fasteners

    HAS_FASTENERS = True
except ImportError:
    HAS_FASTENERS = False


class CrossProcessMicLock:
    def __init__(self, lock_path=None):
        if lock_path is None:
            lock_path = os.path.join(os.getcwd(), "tmp", "mic.lock")
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        self.lock_path = lock_path
        self._thread_lock = threading.Lock()

    def acquire(self):
        self._thread_lock.acquire()
        if HAS_FASTENERS:
            self._inter_lock = fasteners.InterProcessLock(self.lock_path)
            self._inter_lock.acquire()

    def release(self):
        if HAS_FASTENERS:
            try:
                self._inter_lock.release()
            except Exception:
                pass
        self._thread_lock.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args):
        self.release()


def _cleanup_account_state(username):
    user_data_base = os.path.join(os.getcwd(), "user_data")
    login_state_file = os.path.join(user_data_base, f"login_state_{username}.json")
    if os.path.exists(login_state_file):
        try:
            os.remove(login_state_file)
            print(f"[AccountWorker] 已清理登录状态: {login_state_file}")
        except Exception as e:
            print(f"[AccountWorker] 清理登录状态失败: {str(e)}")

    old_login_state = os.path.join(user_data_base, "login_state.json")
    if os.path.exists(old_login_state):
        try:
            with open(old_login_state, "r", encoding="utf-8") as f:
                state = json.load(f)
            if state.get("username") == username:
                os.remove(old_login_state)
                print(
                    f"[AccountWorker] 已清理旧登录状态(用户名匹配): {old_login_state}"
                )
        except Exception:
            pass

    account_user_data_dir = os.path.join(os.getcwd(), f"user_data_{username}")
    if os.path.exists(account_user_data_dir):
        session_files = [
            "Cookies",
            "Cookies-journal",
            "login_state.json",
            "login_state_" + username + ".json",
        ]
        session_dirs = [
            "Local Storage",
            "Session Storage",
            "IndexedDB",
            "Cache",
            "Code Cache",
            "GPUCache",
            "Service Worker",
            "blob_storage",
            "databases",
        ]
        for fname in session_files:
            fpath = os.path.join(account_user_data_dir, fname)
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception:
                    pass
        for dname in session_dirs:
            dpath = os.path.join(account_user_data_dir, dname)
            if os.path.exists(dpath):
                try:
                    import shutil

                    shutil.rmtree(dpath, ignore_errors=True)
                except Exception:
                    pass
        print(f"[AccountWorker] 已清理浏览器会话数据: {account_user_data_dir}")


def _init_account(account_config, tts_manager_config, mic_lock_enabled, priority):
    username = account_config["username"]
    password = account_config["password"]
    drop_level = account_config.get("drop_level", 0.2)
    complexity = account_config.get("complexity", 5)
    target_voice = account_config.get("target_voice", "draft/target_voice.wav")
    vmic_device = (
        account_config.get("vmic_device", None) or app_config.get_default_vmic_device()
    )
    tts_port = account_config.get("tts_port", None)

    from connector.FiFWebClient import FiFWebClient
    from speaker.Speaker import Speaker

    user_data_base = os.path.join(os.getcwd(), "user_data")
    login_state_file = os.path.join(user_data_base, f"login_state_{username}.json")

    if os.path.exists(os.path.join(user_data_base, "login_state.json")):
        if not os.path.exists(login_state_file):
            try:
                old_state_path = os.path.join(user_data_base, "login_state.json")
                with open(old_state_path, "r", encoding="utf-8") as f:
                    old_state = json.load(f)
                old_username = old_state.get("username", "")
                if old_username == username:
                    import shutil

                    shutil.copy2(old_state_path, login_state_file)
                    print(
                        f"[AccountWorker] 已复制旧login_state.json为 {login_state_file} (用户名匹配)"
                    )
                else:
                    print(
                        f"[AccountWorker] 旧login_state.json用户名({old_username})与当前账号({username})不匹配，跳过复制"
                    )
            except Exception as e:
                print(f"[AccountWorker] 检查旧登录状态文件失败: {str(e)}")

    account_user_data_dir = os.path.join(os.getcwd(), f"user_data_{username}")

    if os.path.exists(account_user_data_dir):
        session_files = ["Cookies", "Cookies-journal"]
        session_dirs = [
            "Local Storage",
            "Session Storage",
            "IndexedDB",
            "Cache",
            "Code Cache",
            "GPUCache",
            "Service Worker",
            "blob_storage",
            "databases",
        ]
        for fname in session_files:
            fpath = os.path.join(account_user_data_dir, fname)
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception:
                    pass
        for dname in session_dirs:
            dpath = os.path.join(account_user_data_dir, dname)
            if os.path.exists(dpath):
                try:
                    import shutil

                    shutil.rmtree(dpath, ignore_errors=True)
                except Exception:
                    pass

    fif = FiFWebClient(
        username=username,
        login_state_file=login_state_file,
        user_data_dir=account_user_data_dir,
    )

    user_info = fif.login(username, password)
    print(
        f"[AccountWorker] {user_info['data']['realName']} 登录成功。"
        f"用户ID为{user_info['data']['userId']}。"
    )

    schedule_mode = tts_manager_config.get("schedule_mode", "priority_pipeline")

    gpu_ports = tts_manager_config.get("gpu_ports", [6008])
    cpu_ports = tts_manager_config.get("cpu_ports", [7008])
    cpu_text_threshold = tts_manager_config.get("cpu_text_length_threshold", 15)

    if schedule_mode == "multi_gpu_locked" and tts_port:
        api_url = f"http://127.0.0.1:{tts_port}/tts"
        api_url_cpu = None
    elif schedule_mode == "gpu_cpu_hybrid":
        api_url = f"http://127.0.0.1:{gpu_ports[0]}/tts"
        api_url_cpu = f"http://127.0.0.1:{cpu_ports[0]}/tts" if cpu_ports else None
    else:
        api_url = f"http://127.0.0.1:{gpu_ports[0]}/tts"
        api_url_cpu = None

    print(
        f"[AccountWorker] {username} GPU地址: {api_url}"
        + (f", CPU地址: {api_url_cpu}" if api_url_cpu else "")
    )

    mic_lock = CrossProcessMicLock() if mic_lock_enabled else None

    speaker = Speaker(
        tts_model_name="",
        mode="cuda",
        vmic="VirtualPipeMic",
        target_voice_path=target_voice,
        drop_level=drop_level,
        complexity=complexity,
        mic_lock=mic_lock,
        vmic_device_name=vmic_device,
        tts_api_url=api_url,
        tts_api_url_cpu=api_url_cpu,
        account_priority=priority,
        cpu_text_threshold=cpu_text_threshold,
        username=username,
    )

    print(
        f"[AccountWorker] {username} 当前设置: "
        f"单词丢弃程度={drop_level}, 长难单词复杂度={complexity}"
    )

    return fif, speaker


def _worker_process(
    account_config,
    tts_manager_config,
    mic_lock_enabled,
    priority,
    account_index,
    max_retries=20,
    retry_delay=10,
):
    username = account_config["username"]
    max_retries = tts_manager_config.get("max_retries", max_retries)
    retry_delay = tts_manager_config.get("retry_delay", retry_delay)

    for attempt in range(1, max_retries + 1):
        fif = None
        try:
            print(
                f"[AccountWorker] 账号 {username} (优先级{priority}) "
                f"第{attempt}次尝试执行..."
            )

            fif, speaker = _init_account(
                account_config, tts_manager_config, mic_lock_enabled, priority
            )

            _run_tasks(fif, speaker, username)

            print(f"[AccountWorker] 账号 {username} 所有任务完成!")
            return 0

        except Exception as e:
            print(f"[AccountWorker] 账号 {username} 第{attempt}次尝试出错: {str(e)}")
            traceback.print_exc()

            if fif:
                try:
                    if hasattr(fif, "context") and fif.context:
                        fif.context.close()
                except Exception:
                    pass
                try:
                    if hasattr(fif, "playwright") and fif.playwright:
                        fif.playwright.stop()
                except Exception:
                    pass
                fif = None

            if attempt < max_retries:
                _cleanup_account_state(username)

                print(
                    f"[AccountWorker] 账号 {username} 将在{retry_delay}秒后重试 "
                    f"({attempt}/{max_retries})..."
                )
                time.sleep(retry_delay)
            else:
                print(
                    f"[AccountWorker] 账号 {username} 已达到最大重试次数({max_retries})，放弃。"
                )
                return 1

    return 1


def _run_tasks(fif, speaker, username):
    task_list_resp = fif.get_task_list(fif.get_page())
    if task_list_resp.get("status") == -1:
        raise Exception("获取任务列表失败")

    for i, task in enumerate(task_list_resp["data"]["ttiList"]):
        ttd_list = fif.get_ttd_list(fif.get_page(), task["id"])
        print(
            f"[AccountWorker] {username} 正在开始第{i + 1}个任务。"
            f"任务代码为{task['id']}。任务名为{task['taskName']}。"
        )

        for j, ttd in enumerate(ttd_list["data"]["ttdList"]):
            print(
                f"[AccountWorker] {username} 正在开始第{j + 1}个单元。"
                f"单元代码为{ttd['id']}。单元名为{ttd['unitName']}。"
            )
            unit_info = fif.get_unit_info(
                fif.get_page(), ttd["unitid"], task["taskId"]
            )["data"]
            print(
                f"[AccountWorker] {username} 正在开始第{j + 1}个单元。"
                f"单元代码为{unit_info['id']}。"
            )

            for k, level in enumerate(unit_info["levelList"]):
                if level["levelScore"] >= 60:
                    print(
                        f"[AccountWorker] {username} 等级{level['levelName']}超过目标分数。已跳过。"
                    )
                    continue

                print(
                    f"[AccountWorker] {username} 正在开始第{k + 1}个等级。"
                    f"等级代码为{level['levelId']}。等级名为{level['levelName']}。"
                )

                try:
                    fif.start_level_test(
                        fif.get_page(),
                        speaker,
                        unit_id=unit_info["id"],
                        task_id=task["id"],
                        level_id=level["levelId"],
                    )
                    print(f"[AccountWorker] {username} 第{k + 1}个等级完成。")
                except Exception as level_err:
                    print(
                        f"[AccountWorker] {username} 第{k + 1}个等级执行出错: {str(level_err)}"
                    )
                    is_browser_error = any(
                        kw in str(level_err)
                        for kw in [
                            "Target page",
                            "TargetClosedError",
                            "Browser has been closed",
                            "context or browser",
                        ]
                    )
                    if is_browser_error:
                        print(
                            f"[AccountWorker] {username} 检测到浏览器崩溃，终止当前账号任务循环以触发重试..."
                        )
                        raise
                    print(f"[AccountWorker] {username} 跳过此等级，继续下一个等级...")


class AccountWorker:
    def __init__(
        self,
        account_config,
        tts_manager_config,
        mic_lock_enabled,
        priority,
        account_index=0,
    ):
        self.account_config = account_config
        self.tts_manager_config = tts_manager_config
        self.mic_lock_enabled = mic_lock_enabled
        self.priority = priority
        self.account_index = account_index
        self.username = account_config["username"]
        self.process = None
        self.result = None
        self.error = None

    def run(self):
        p = multiprocessing.Process(
            target=_worker_process,
            args=(
                self.account_config,
                self.tts_manager_config,
                self.mic_lock_enabled,
                self.priority,
                self.account_index,
            ),
            daemon=True,
        )
        self.process = p
        p.start()

    def join(self, timeout=None):
        if self.process:
            self.process.join(timeout=timeout)

    def is_alive(self):
        return self.process is not None and self.process.is_alive()

    def stop(self):
        if self.process and self.process.is_alive():
            self.process.terminate()

    def get_exit_code(self):
        if self.process:
            return self.process.exitcode
        return None
