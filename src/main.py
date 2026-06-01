# 全局变量用于存储API服务器进程
api_process = None

import os, time, subprocess, sys, threading


def start_api_server():
    global api_process

    """
    启动FastAPI TTS服务器作为子进程，并添加调试信息
    """
    try:
        # 直接使用绝对路径，避免路径拼接错误
        api_script = r"D:\University\More\AI\Echo\index-tts\index-tts\api_server.py"

        # 设置API服务器的工作目录为api_server.py所在的目录
        api_working_dir = os.path.dirname(api_script)

        # 检查API脚本是否存在
        if not os.path.exists(api_script):
            print(f"[错误] API脚本不存在: {api_script}")
            print(f"[调试] 当前工作目录: {os.getcwd()}")
            print(f"[调试] 脚本期望路径: {api_script}")
            return None

        print(f"[调试] 找到API脚本: {api_script}")

        # 构建命令
        cmd = [sys.executable, api_script]
        print(f"[调试] 执行命令: {' '.join(cmd)}")

        # 读取配置文件获取 use_gpu 参数
        use_gpu = True
        if os.path.exists("user.json"):
            try:
                with io.open("user.json") as f:
                    config = json.load(f)
                    use_gpu = config.get("use_gpu", True)  # 默认使用 GPU
            except Exception as e:
                print(f"[警告] 读取 use_gpu 配置失败: {str(e)}，使用默认值 True")

        # 设置环境变量
        env = os.environ.copy()
        if use_gpu:
            print("[调试] 使用 GPU 模式运行")
            env["CUDA_VISIBLE_DEVICES"] = "0"  # 使用第一个 GPU
        else:
            print("[调试] 使用 CPU 模式运行")
            env["CUDA_VISIBLE_DEVICES"] = "-1"  # 禁用所有 GPU
            env["FORCE_CPU"] = "1"  # 强制使用 CPU

        # 直接输出到当前终端，不捕获输出
        process = subprocess.Popen(
            cmd,
            stdout=None,  # 直接继承主进程的stdout
            stderr=None,  # 直接继承主进程的stderr
            cwd=api_working_dir,
            env=env,  # 传入修改后的环境变量
        )

        # 等待一些时间让进程启动
        time.sleep(10)

        # 检查进程状态
        return_code = process.poll()
        if return_code is not None:
            print(f"[错误] API服务器进程已退出，返回码: {return_code}")
            return None

        print("[调试] API服务器进程正在运行")

        # 简单检查API服务器是否准备好
        try:
            import requests

            time.sleep(5)  # 给服务器一点时间启动
            response = requests.get("http://127.0.0.1:6008/", timeout=1)
            if response.status_code == 200:
                print("[调试] API服务器确认正常运行")
            else:
                print(f"[警告] API服务器返回非200状态: {response.status_code}")
        except Exception as e:
            print(f"[服务器检查] 无法立即确认服务器状态: {str(e)}")
            print("[信息] 但这不影响程序继续运行")

        # 将API进程赋值给全局变量
        api_process = process
        return process

    except Exception as e:
        print(f"[错误] 启动API服务器时发生异常: {str(e)}")
        import traceback

        traceback.print_exc()
        return None


# 添加清理函数
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


import io
import json

from connector.FiFWebClient import FiFWebClient
from speaker.Speaker import Speaker


def run_main():
    global api_process

    print("[main] 正在检测环境并加载神经网络。")

    print("[main] FiF口语,启动!")

    fif = FiFWebClient()

    # 从配置文件读取丢弃程度和复杂度参数
    with io.open("user.json") as f:
        user_json = json.load(f)
        username = user_json["username"]
        password = user_json["password"]
        drop_level = user_json.get("drop_level", 0.2)  # 默认丢弃程度
        complexity = user_json.get("complexity", 5)  # 默认复杂度

    speaker = Speaker(
        "", "cuda", "VirtualPipeMic", "draft/target_voice.wav", drop_level, complexity
    )

    user_info = fif.login(username, password)

    print(
        "[main] {}登录成功。用户ID为{}。".format(
            user_info["data"]["realName"], user_info["data"]["userId"]
        )
    )

    # 添加交互式控制选项
    print(
        "[main] 当前设置: 单词丢弃程度={}, 长难单词复杂度={}".format(
            drop_level, complexity
        )
    )
    # print(
    #     "[main] 输入 'd 值' 调整丢弃程度 (0-1), 输入 'c 值' 调整复杂度 (最小字符数), 直接回车继续:"
    # )

    # user_input = input().strip()
    # if user_input:
    #     if user_input.startswith("d "):
    #         try:
    #             new_drop = float(user_input[2:])
    #             if 0 <= new_drop <= 1:
    #                 speaker.set_drop_level(new_drop)
    #             else:
    #                 print("[main] 丢弃程度必须在0-1之间")
    #         except ValueError:
    #             print("[main] 请输入有效的数字")
    #     elif user_input.startswith("c "):
    #         try:
    #             new_comp = int(user_input[2:])
    #             if new_comp > 0:
    #                 speaker.set_complexity(new_comp)
    #             else:
    #                 print("[main] 复杂度必须大于0")
    #         except ValueError:
    #             print("[main] 请输入有效的整数")

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

                # # ? FiF口语网页端似乎没有实现问答类型题目，它无法录音。故跳过。
                # if "问答" in level["levelName"] and not "简短问答" in level["levelName"]:
                #     print("[main] 第{}个等级为问答题。已跳过。".format(k + 1))
                #     continue

                fif.start_level_test(
                    fif.get_page(),
                    speaker,
                    unit_id=unit_info["id"],
                    task_id=task["id"],
                    level_id=level["levelId"],
                ),

                print("[main] 第{}个等级完成。".format(k + 1))


def restart_program():
    """在新进程中重启程序"""
    print("[重启] 正在准备重启程序...")

    # 获取当前脚本的路径
    current_script = os.path.abspath(__file__)

    # 构建重启命令
    restart_cmd = [sys.executable, current_script]

    print(f"[重启] 重启命令: {' '.join(restart_cmd)}")

    # 在新进程中启动程序
    # 使用 CREATE_NEW_PROCESS_GROUP 标志确保完全独立的进程
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    subprocess.Popen(restart_cmd, creationflags=creationflags)

    print("[重启] 新进程已启动，当前进程将退出。")


if __name__ == "__main__":
    import atexit

    # 检查是否是重启的进程（通过环境变量）
    is_restart = os.environ.get("FIF_RESTART_COUNT", "0")
    restart_count = int(is_restart)
    max_retries = 20

    # 设置当前重启计数
    os.environ["FIF_RESTART_COUNT"] = str(restart_count + 1)

    if restart_count > 0:
        print(f"[重启] 程序已重启 (第{restart_count}次)")

    try:
        api_process = start_api_server()

        if api_process is None:
            print("[错误] 无法启动API服务器，等待5秒后重试...")
            if restart_count < max_retries:
                time.sleep(5)
                restart_program()
            else:
                print(f"[错误] 已达到最大重试次数({max_retries})，程序退出。")
            sys.exit(1)

        atexit.register(cleanup)

        run_main()

        print("[main] 程序正常完成。")

    except KeyboardInterrupt:
        print("\n[main] 用户中断程序，正在退出...")
        cleanup()
        sys.exit(0)

    except Exception as e:
        print(f"[错误] 程序运行时发生异常: {str(e)}")
        import traceback

        traceback.print_exc()

        if restart_count < max_retries:
            print(
                f"[重启] 程序将在5秒后自动重启 (第{restart_count + 1}/{max_retries}次重试)..."
            )

            if "获取任务列表失败" in str(e):
                login_state_path = (
                    r"D:\University\More\fif\fuckfif\src\user_data\login_state.json"
                )
                if os.path.exists(login_state_path):
                    print(f"[清理] 检测到登录状态错误，正在删除 {login_state_path}")
                    try:
                        os.remove(login_state_path)
                        print("[清理] login_state.json 已删除")
                    except Exception as remove_error:
                        print(f"[警告] 删除 login_state.json 失败: {str(remove_error)}")

            cleanup()
            time.sleep(5)
            restart_program()
        else:
            print(f"[错误] 已达到最大重试次数({max_retries})，程序退出。")
            cleanup()
            sys.exit(1)
