import time
import multiprocessing
from .tts_manager import TTSManager
from .account_worker import AccountWorker


class TaskScheduler:
    def __init__(self, config):
        self.config = config
        self.tts_manager = TTSManager(config)
        self.workers = []
        self.schedule_mode = config.get("schedule_mode", "priority_pipeline")

    def start(self):
        print(f"[TaskScheduler] 调度模式: {self.schedule_mode}")

        if not self.tts_manager.start():
            print("[TaskScheduler] TTS管理器启动失败!")
            return False

        accounts = self.config.get("accounts", [])
        if not accounts:
            print("[TaskScheduler] 没有配置任何账号!")
            return False

        sorted_accounts = sorted(
            enumerate(accounts), key=lambda x: x[1].get("priority", x[0] + 1)
        )

        if self.schedule_mode == "sequential":
            self._run_sequential(sorted_accounts)
        elif self.schedule_mode in (
            "priority_pipeline",
            "gpu_cpu_hybrid",
            "multi_gpu_locked",
        ):
            self._run_parallel(sorted_accounts, stagger=True)
        else:
            print(
                f"[TaskScheduler] 未知调度模式: {self.schedule_mode}, 使用priority_pipeline"
            )
            self.schedule_mode = "priority_pipeline"
            self._run_parallel(sorted_accounts, stagger=True)

        return True

    def _run_sequential(self, sorted_accounts):
        print("[TaskScheduler] 串行模式: 账号按优先级逐个执行")
        for idx, account in sorted_accounts:
            priority = account.get("priority", idx + 1)
            worker = AccountWorker(
                account_config=account,
                tts_manager_config=self.config,
                mic_lock_enabled=False,
                priority=priority,
                account_index=idx,
            )
            worker.run()
            worker.join()

            exit_code = worker.get_exit_code()
            if exit_code != 0:
                print(
                    f"[TaskScheduler] 账号 {account['username']} 执行出错 (退出码: {exit_code})"
                )
            else:
                print(f"[TaskScheduler] 账号 {account['username']} 执行完成")

    def _run_parallel(self, sorted_accounts, stagger=False):
        print("[TaskScheduler] 并行模式: 账号按优先级并行执行(多进程)")
        stagger_delay = self.config.get("stagger_delay", 15)

        mic_lock_enabled = True

        for idx, account in sorted_accounts:
            priority = account.get("priority", idx + 1)
            worker = AccountWorker(
                account_config=account,
                tts_manager_config=self.config,
                mic_lock_enabled=mic_lock_enabled,
                priority=priority,
                account_index=idx,
            )
            self.workers.append(worker)
            worker.run()

            if stagger and idx < len(sorted_accounts) - 1:
                print(f"[TaskScheduler] 等待{stagger_delay}秒后启动下一个账号...")
                time.sleep(stagger_delay)

        print("[TaskScheduler] 所有账号已启动，等待完成...")
        for worker in self.workers:
            worker.join()

        for worker in self.workers:
            exit_code = worker.get_exit_code()
            username = worker.username
            if exit_code == 0:
                print(f"[TaskScheduler] 账号 {username}: 成功")
            else:
                print(f"[TaskScheduler] 账号 {username}: 失败 (退出码: {exit_code})")

    def stop(self):
        print("[TaskScheduler] 正在停止所有工作进程...")
        for worker in self.workers:
            worker.stop()
        self.tts_manager.stop()
        print("[TaskScheduler] 所有工作进程已停止")

    def get_results(self):
        results = []
        for w in self.workers:
            exit_code = w.get_exit_code()
            results.append(
                {
                    "username": w.username,
                    "result": "success" if exit_code == 0 else "error",
                    "exit_code": exit_code,
                }
            )
        return results
