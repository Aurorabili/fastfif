"""
多账号调度配置说明

配置文件: user.json (与main.py同目录)

=== user.json 完整配置说明 ===

一、旧格式(单账号，向后兼容):
{
    "username": "账号",
    "password": "密码",
    "drop_level": 0,
    "complexity": 6,
    "use_gpu": true
}
旧格式会自动转换为新格式运行，行为与原来完全一致。

二、新格式(多账号)完整示例:
{
    "schedule_mode": "priority_pipeline",
    "max_gpu_instances": 1,
    "max_cpu_instances": 0,
    "cpu_text_length_threshold": 15,
    "stagger_delay": 15,
    "max_retries": 3,
    "retry_delay": 10,
    "gpu_ports": [6008],
    "cpu_ports": [7008],
    "api_script": "D:\\path\\to\\index-tts\\api_server.py",
    "translation_model_path": "D:\\path\\to\\m2m100_418M",
    "translation_model_type": "m2m100_418M",
    "browser_channel": "msedge",
    "viewport": [1200, 800],
    "default_vmic_device": "CABLE Input (VB-Audio Virtual Cable)",
    "login_state_expire_days": 7,
    "accounts": [...]
}

=== 调度配置项 ===

schedule_mode (调度模式):
  - "sequential":        严格串行，账号按优先级逐个执行。最安全，零超时风险。
                         适合: 账号少、不急的情况。
  - "priority_pipeline": 优先级流水线(推荐)。1个GPU实例串行推理，多账号浏览器并行操作。
                         TTS推理互不竞争不会超时，虚拟麦克风互斥避免串音。
                         单虚拟麦克风时自动静音其他浏览器防止串音。
                         适合: 2-3个账号，希望加速但不冒险。
  - "gpu_cpu_hybrid":    GPU+CPU混合。1个GPU+1个CPU实例，智能路由:
                         - 长文本(词数>阈值) → 必须走GPU(CPU会超时)
                         - 短文本(词数<=阈值) + GPU空闲 → 走GPU(更快,~3s)
                         - 短文本(词数<=阈值) + GPU忙于长推理 → 走CPU(避免等GPU,~10s)
                         GPU和CPU两个TTS服务器独立运行，推理互不阻塞。
                         CPU实例失败时自动回退到GPU。
                         适合: 2个账号，希望短文本不被长文本阻塞。
  - "multi_gpu_locked":  多GPU实例+推理锁。最多3个GPU实例，全局推理锁保证同时只有1个推理。
                         每个账号绑定独立TTS实例，无需切换模型。
                         需要多个虚拟音频线缆(VB-Audio Cable A/B/C)。
                         适合: 3个账号、VRAM充裕、已安装多个虚拟音频线缆。

max_gpu_instances: GPU上运行的TTS实例数量。
  - sequential / priority_pipeline: 固定为1
  - gpu_cpu_hybrid: 通常为1
  - multi_gpu_locked: 1-3 (每个实例约占2GB+ VRAM，8GB显卡最多3个)

max_cpu_instances: CPU上运行的TTS实例数量。
  - 仅 gpu_cpu_hybrid 模式有效，通常为0或1
  - CPU推理单实例占60-80% CPU，只能1个

cpu_text_length_threshold: CPU分流阈值(单词数)。
  - 仅 gpu_cpu_hybrid 模式有效
  - 文本单词数 <= 此值时为短文本，可能走CPU(取决于GPU是否忙碌)
  - 文本单词数 > 此值时为长文本，必须走GPU(CPU会超时)
  - 建议值: 10-20，取决于CPU性能

stagger_delay: 账号启动间隔(秒)。
  - 并行模式下，每个账号启动后等待此秒数再启动下一个
  - 用于错开各账号的TTS请求时间，降低GPU竞争概率
  - 建议值: 10-30

max_retries: 每个账号出错后最大重试次数。0=不重试，默认3。
retry_delay: 重试间隔秒数，默认10。

gpu_ports: GPU实例的端口号列表。长度应 >= max_gpu_instances。默认: [6008]
cpu_ports: CPU实例的端口号列表。长度应 >= max_cpu_instances。默认: [7008]

=== 路径与环境配置项 ===

api_script: IndexTTS API服务器脚本的绝对路径。
  - 示例: "D:\\University\\More\\AI\\Echo\\index-tts\\index-tts\\api_server.py"
  - 此脚本由TTSManager启动，用于提供TTS推理HTTP服务

translation_model_path: 翻译模型(m2m100)目录的绝对路径。
  - 示例: "D:\\University\\More\\translate_model\\m2m100_418M"
  - 用于中英文翻译，辅助答题

translation_model_type: 翻译模型类型。默认 "m2m100_418M"。

browser_channel: 浏览器类型。
  - "msedge": Microsoft Edge (默认)
  - "chrome": Google Chrome
  - "chromium": Chromium

viewport: 浏览器窗口大小 [宽, 高]。默认 [1200, 800]。

default_vmic_device: 默认虚拟麦克风设备名。
  - 账号级 vmic_device 未配置时使用此值
  - 默认: "CABLE Input (VB-Audio Virtual Cable)"

login_state_expire_days: 登录状态过期天数。默认7。

=== 账号配置项说明 ===

username (必填): 登录账号
password (必填): 登录密码
priority (可选): 优先级，1最高，数字越大越低。默认按数组顺序(1,2,3...)
drop_level (可选): 单词丢弃程度(0-1)，0=不丢弃。默认0.2
complexity (可选): 长难单词复杂度(最小字符数)。默认5
target_voice (可选): 目标语音文件路径。默认 "draft/target_voice.wav"
vmic_device (可选): 虚拟音频设备名称。未配置时使用 default_vmic_device。
  - 单虚拟麦克风时(priority_pipeline/gpu_cpu_hybrid)，程序自动静音其他浏览器防串音
  - multi_gpu_locked模式建议每个账号配置不同的虚拟线缆:
    "CABLE Input (VB-Audio Virtual Cable)"   (VB-Audio Cable A)
    "CABLE Input (VB-Audio Virtual Cable B)"  (VB-Audio Cable B)
    "CABLE Input (VB-Audio Virtual Cable C)"  (VB-Audio Cable C)
tts_port (可选): 绑定的TTS实例端口。仅 multi_gpu_locked 模式有效。

=== 登录状态文件说明 ===
多账号模式下，每个账号的登录状态保存在独立文件中:
  user_data/login_state_<username>.json
旧的单文件 user_data/login_state.json 会被自动迁移。
出错重试时会自动清理过期登录状态。

=== 串音防护说明 ===
单虚拟麦克风模式下(priority_pipeline/gpu_cpu_hybrid)，程序通过以下机制防止串音:
  1. 虚拟麦克风互斥锁: 同一时刻只有一个账号播放音频
  2. 浏览器麦克风静音: 播放账号的浏览器保持麦克风开启，其他浏览器自动静音
  3. 静音通过JavaScript控制 MediaStreamTrack.enabled 实现，不中断录音流

=== 推荐配置示例 ===

1. 最简单: 2个账号，推荐配置
{
    "schedule_mode": "priority_pipeline",
    "max_gpu_instances": 1,
    "max_cpu_instances": 0,
    "stagger_delay": 15,
    "api_script": "D:\\path\\to\\api_server.py",
    "translation_model_path": "D:\\path\\to\\m2m100_418M",
    "accounts": [
        {"username": "acc1", "password": "pw1", "priority": 1, "drop_level": 0, "complexity": 6},
        {"username": "acc2", "password": "pw2", "priority": 2, "drop_level": 0.2, "complexity": 5}
    ]
}

2. 3个账号，有多个虚拟线缆
{
    "schedule_mode": "multi_gpu_locked",
    "max_gpu_instances": 3,
    "stagger_delay": 10,
    "gpu_ports": [6008, 6009, 6010],
    "api_script": "D:\\path\\to\\api_server.py",
    "translation_model_path": "D:\\path\\to\\m2m100_418M",
    "accounts": [
        {"username": "acc1", "password": "pw1", "priority": 1, "tts_port": 6008,
         "vmic_device": "CABLE Input (VB-Audio Virtual Cable)"},
        {"username": "acc2", "password": "pw2", "priority": 2, "tts_port": 6009,
         "vmic_device": "CABLE Input (VB-Audio Virtual Cable B)"},
        {"username": "acc3", "password": "pw3", "priority": 3, "tts_port": 6010,
         "vmic_device": "CABLE Input (VB-Audio Virtual Cable C)"}
    ]
}

3. 2个账号，GPU+CPU混合
{
    "schedule_mode": "gpu_cpu_hybrid",
    "max_gpu_instances": 1,
    "max_cpu_instances": 1,
    "cpu_text_length_threshold": 15,
    "gpu_ports": [6008],
    "cpu_ports": [7008],
    "api_script": "D:\\path\\to\\api_server.py",
    "translation_model_path": "D:\\path\\to\\m2m100_418M",
    "accounts": [
        {"username": "acc1", "password": "pw1", "priority": 1},
        {"username": "acc2", "password": "pw2", "priority": 2}
    ]
}
"""

import os
import sys
import io
import json
import time
import subprocess
import traceback

import config as app_config

api_process = None


def start_api_server():
    global api_process

    try:
        api_script = app_config.get_api_script()
        api_working_dir = os.path.dirname(api_script)

        if not os.path.exists(api_script):
            print(f"[错误] API脚本不存在: {api_script}")
            print(f"[调试] 当前工作目录: {os.getcwd()}")
            print(f"[调试] 脚本期望路径: {api_script}")
            return None

        print(f"[调试] 找到API脚本: {api_script}")

        cmd = [sys.executable, api_script]
        print(f"[调试] 执行命令: {' '.join(cmd)}")

        use_gpu = True
        if os.path.exists("user.json"):
            try:
                with io.open("user.json", encoding="utf-8") as f:
                    config = json.load(f)
                if "accounts" in config:
                    use_gpu = config.get("use_gpu", True)
                else:
                    use_gpu = config.get("use_gpu", True)
            except Exception as e:
                print(f"[警告] 读取 use_gpu 配置失败: {str(e)}，使用默认值 True")

        env = os.environ.copy()
        if use_gpu:
            print("[调试] 使用 GPU 模式运行")
            env["CUDA_VISIBLE_DEVICES"] = "0"
        else:
            print("[调试] 使用 CPU 模式运行")
            env["CUDA_VISIBLE_DEVICES"] = "-1"
            env["FORCE_CPU"] = "1"

        process = subprocess.Popen(
            cmd,
            stdout=None,
            stderr=None,
            cwd=api_working_dir,
            env=env,
        )

        time.sleep(10)

        return_code = process.poll()
        if return_code is not None:
            print(f"[错误] API服务器进程已退出，返回码: {return_code}")
            return None

        print("[调试] API服务器进程正在运行")

        try:
            import requests

            time.sleep(5)
            response = requests.get("http://127.0.0.1:6008/", timeout=1)
            if response.status_code == 200:
                print("[调试] API服务器确认正常运行")
            else:
                print(f"[警告] API服务器返回非200状态: {response.status_code}")
        except Exception as e:
            print(f"[服务器检查] 无法立即确认服务器状态: {str(e)}")
            print("[信息] 但这不影响程序继续运行")

        api_process = process
        return process

    except Exception as e:
        print(f"[错误] 启动API服务器时发生异常: {str(e)}")
        traceback.print_exc()
        return None


def cleanup():
    global api_process
    if api_process and api_process.poll() is None:
        print("[清理] 正在终止API服务器...")
        api_process.terminate()
        try:
            api_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            api_process.kill()
        print("[清理] API服务器已终止")


def load_config():
    config_path = os.path.join(os.getcwd(), "user.json")
    if not os.path.exists(config_path):
        print("[错误] user.json 不存在!")
        sys.exit(1)

    with io.open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    if "accounts" not in config:
        print("[main] 检测到旧格式配置(单账号)，自动转换为新格式...")
        config = _convert_legacy_config(config)

    return config


def _convert_legacy_config(old_config):
    account = {
        "username": old_config["username"],
        "password": old_config["password"],
        "priority": 1,
        "drop_level": old_config.get("drop_level", 0.2),
        "complexity": old_config.get("complexity", 5),
        "target_voice": "draft/target_voice.wav",
    }

    use_gpu = old_config.get("use_gpu", True)

    new_config = {
        "schedule_mode": "sequential",
        "max_gpu_instances": 1 if use_gpu else 0,
        "max_cpu_instances": 0 if use_gpu else 1,
        "gpu_ports": [6008],
        "cpu_ports": [7008],
        "stagger_delay": 0,
        "accounts": [account],
        "_legacy": True,
    }

    print(f"[main] 旧格式转换完成: 账号={account['username']}, GPU={use_gpu}")
    return new_config


def run_main():
    global api_process

    print("[main] 正在检测环境并加载神经网络。")
    print("[main] FiF口语,启动!")

    config = load_config()

    is_legacy = config.get("_legacy", False)
    accounts = config.get("accounts", [])
    schedule_mode = config.get("schedule_mode", "priority_pipeline")

    if is_legacy:
        print("[main] 兼容模式: 使用旧的单账号流程")
        api_process = start_api_server()
        if api_process is None:
            print("[错误] 无法启动API服务器")
            sys.exit(1)

        from connector.FiFWebClient import FiFWebClient
        from speaker.Speaker import Speaker

        account = accounts[0]
        fif = FiFWebClient(username=account["username"])

        with io.open("user.json", encoding="utf-8") as f:
            user_json = json.load(f)

        username = account["username"]
        password = account["password"]
        drop_level = account.get("drop_level", 0.2)
        complexity = account.get("complexity", 5)

        speaker = Speaker(
            "",
            "cuda",
            "VirtualPipeMic",
            account.get("target_voice", "draft/target_voice.wav"),
            drop_level,
            complexity,
        )

        user_info = fif.login(username, password)
        print(
            "[main] {}登录成功。用户ID为{}。".format(
                user_info["data"]["realName"], user_info["data"]["userId"]
            )
        )
        print(
            "[main] 当前设置: 单词丢弃程度={}, 长难单词复杂度={}".format(
                drop_level, complexity
            )
        )

        _run_single_account(fif, speaker, username)
        print("[main] 程序正常完成。")
        return

    print(f"[main] 多账号调度模式: {schedule_mode}")
    print(f"[main] 共 {len(accounts)} 个账号")

    from scheduler.task_scheduler import TaskScheduler

    scheduler = TaskScheduler(config)

    try:
        scheduler.start()
        print("[main] 所有账号任务执行完毕。")
        results = scheduler.get_results()
        has_failure = False
        for r in results:
            status = (
                "成功"
                if r["result"] == "success"
                else f"失败(退出码: {r.get('exit_code', 'unknown')})"
            )
            print(f"[main] 账号 {r['username']}: {status}")
            if r["result"] != "success":
                has_failure = True
        if has_failure:
            print("[main] 部分账号执行失败，请检查日志。")
    except Exception as e:
        print(f"[错误] 调度器运行出错: {str(e)}")
        traceback.print_exc()
    finally:
        scheduler.stop()

    print("[main] 程序正常完成。")


def _run_single_account(fif, speaker, username):
    for i, task in enumerate(fif.get_task_list(fif.get_page())["data"]["ttiList"]):
        ttd_list = fif.get_ttd_list(fif.get_page(), task["id"])
        print(
            "[main] 正在开始第{}个任务。任务代码为{}。任务名为{}。".format(
                i + 1, task["id"], task["taskName"]
            )
        )
        for j, ttd in enumerate(ttd_list["data"]["ttdList"]):
            print(
                "[main] 正在开始第{}个单元。单元代码为{}。单元名为{}。".format(
                    j + 1, ttd["id"], ttd["unitName"]
                )
            )
            unit_info = fif.get_unit_info(
                fif.get_page(), ttd["unitid"], task["taskId"]
            )["data"]
            print(
                "[main] 正在开始第{}个单元。单元代码为{}。".format(
                    j + 1, unit_info["id"]
                )
            )
            for k, level in enumerate(unit_info["levelList"]):
                if level["levelScore"] >= 60:
                    print(
                        "[main] 等级{}超过目标分数。已跳过。".format(level["levelName"])
                    )
                    continue
                print(
                    "[main] 正在开始第{}个等级。等级代码为{}。等级名为{}。".format(
                        k + 1, level["levelId"], level["levelName"]
                    )
                )

                fif.start_level_test(
                    fif.get_page(),
                    speaker,
                    unit_id=unit_info["id"],
                    task_id=task["id"],
                    level_id=level["levelId"],
                ),

                print("[main] 第{}个等级完成。".format(k + 1))


def restart_program():
    print("[重启] 正在准备重启程序...")
    current_script = os.path.abspath(__file__)
    restart_cmd = [sys.executable, current_script]
    print(f"[重启] 重启命令: {' '.join(restart_cmd)}")
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(restart_cmd, creationflags=creationflags)
    print("[重启] 新进程已启动，当前进程将退出。")


if __name__ == "__main__":
    import atexit

    is_restart = os.environ.get("FIF_RESTART_COUNT", "0")
    restart_count = int(is_restart)
    max_retries = 20

    os.environ["FIF_RESTART_COUNT"] = str(restart_count + 1)

    if restart_count > 0:
        print(f"[重启] 程序已重启 (第{restart_count}次)")

    try:
        run_main()

    except KeyboardInterrupt:
        print("\n[main] 用户中断程序，正在退出...")
        cleanup()
        sys.exit(0)

    except Exception as e:
        print(f"[错误] 程序运行时发生异常: {str(e)}")
        traceback.print_exc()

        if restart_count < max_retries:
            print(
                f"[重启] 程序将在5秒后自动重启 (第{restart_count + 1}/{max_retries}次重试)..."
            )

            if "获取任务列表失败" in str(e):
                login_state_path = r"user_data\login_state.json"
                if os.path.exists(login_state_path):
                    print(f"[清理] 检测到登录状态错误，正在删除 {login_state_path}")
                    try:
                        os.remove(login_state_path)
                        print("[清理] login_state.json 已删除")
                    except Exception as remove_error:
                        print(f"[警告] 删除 login_state.json 失败: {str(remove_error)}")

                user_data_dir = os.path.join(os.getcwd(), "user_data")
                for fname in os.listdir(user_data_dir):
                    if fname.startswith("login_state_") and fname.endswith(".json"):
                        fpath = os.path.join(user_data_dir, fname)
                        try:
                            os.remove(fpath)
                            print(f"[清理] 已删除 {fpath}")
                        except Exception as remove_error:
                            print(f"[警告] 删除 {fpath} 失败: {str(remove_error)}")

            cleanup()
            time.sleep(5)
            restart_program()
        else:
            print(f"[错误] 已达到最大重试次数({max_retries})，程序退出。")
            cleanup()
            sys.exit(1)
