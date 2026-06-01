import json
import os
import time
import random
from playwright.sync_api import Page, sync_playwright
from transformers import (
    M2M100ForConditionalGeneration,
    M2M100Tokenizer,
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
)
import torch
import re


class FiFWebClient:
    urls = {
        "login": "https://www.fifedu.com/iplat/fifLogin/index.html?v=5.4.1",
        "ai_task": "https://static.fifedu.com/static/fiforal/kyxl-web-static/student-h5/index.html#/pages/teaching/teaching",
        "unit_test": "https://static.fifedu.com/static/fiforal/kyxl-web-static/student-h5/index.html#/pages/webView/testWebView/testWebView?userId={}&taskId={}&unitId={}&gId={}",
    }
    api_urls = {
        "get_user_info": "https://www.fifedu.com/iplatform-zjzx/common/connect",
        "get_task_list": "https://moral.fifedu.com/kyxl-app/stu/task/teaTaskList",
        "get_task_detail": "https://moral.fifedu.com/kyxl-app/task/stu/teaTaskDetail",
        "get_unit_info": "https://moral.fifedu.com/kyxl-app/stu/column/stuUnitInfo?unitId={}&taskId={}",
        "post_test_results": "https://moral.fifedu.com/kyxl-app-challenge/evaluation/submitChallengeResults",
        "get_test_info": "https://moral.fifedu.com/kyxl-app/column/getLevelInfo",
    }
    user_auth = {"token": None, "source": None}
    user_info = None

    # 随机UA池
    USER_AGENTS = [
        # Windows 10 - Chrome
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.159 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.88 Safari/537.36",
        # Windows 10 - Edge
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.159 Safari/537.36 Edg/119.0.2151.72",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.88 Safari/537.36 Edg/118.0.2088.76",
        # Windows 10 - Firefox
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
        # macOS - Safari
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        # macOS - Chrome
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.159 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.88 Safari/537.36",
    ]

    def __init__(
        self,
        auth_mode="auto",
        username=None,
        translation_model_path=r"D:\University\More\translate_model\m2m100_418M",
        translation_model_type=r"m2m100_418M",
    ):
        """
        初始化FiFWebClient

        Args:
            auth_mode (str): 认证模式，可选值：
                - "auto": 自动尝试使用保存的登录状态，如果失败则重新登录
                - "force_login": 强制重新登录
                - "saved_only": 仅使用保存的登录状态，如果失败则抛出异常
            username (str): 用户名，用于验证保存的登录状态是否匹配
        """
        self.auth_mode = auth_mode
        self.username = username
        self.translation_model_path = translation_model_path
        self.translation_model_type = translation_model_type
        self.translation_model = None
        self.tokenizer = None

        # 如果提供了模型路径，预加载翻译模型
        if self.translation_model_path and os.path.exists(self.translation_model_path):
            self._load_translation_model()

        self.playwright = sync_playwright().start()

        # 随机选择一个User-Agent
        user_agent = random.choice(self.USER_AGENTS)
        print(f"使用User-Agent: {user_agent}")

        # 定义用户数据目录路径
        user_data_dir = os.path.join(os.getcwd(), "user_data")

        # 如果用户数据目录不存在，创建一个默认的
        if not os.path.exists(user_data_dir):
            os.makedirs(user_data_dir)
            print(f"创建新的用户数据目录: {user_data_dir}")
        else:
            print(f"使用现有的用户数据目录: {user_data_dir}")

        # 在浏览器启动参数中添加静音选项
        browser_args = [
            "--mute-audio",  # 静音
            "--autoplay-policy=no-user-gesture-required",  # 允许自动播放
            "--disable-features=AudioService",  # 禁用音频服务
        ]

        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            channel="msedge",
            permissions=["microphone"],
            user_agent=user_agent,
            viewport={"width": 1200, "height": 800},
            ignore_https_errors=True,
            java_script_enabled=True,
            bypass_csp=True,
            args=browser_args,  # 添加启动参数
        )

        # 从持久化上下文中获取页面
        self.page = (
            self.context.pages[0] if self.context.pages else self.context.new_page()
        )

        # 添加执行脚本以隐藏自动化特征
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)

        # 保存浏览器实例引用
        self.browser = self.context.browser

    def __del__(self):
        if hasattr(self, "browser") and self.browser:
            self.browser.close()
        if hasattr(self, "playwright") and self.playwright:
            self.playwright.stop()

    def _load_translation_model(self):
        """加载翻译模型"""
        if not self.translation_model_path or not os.path.exists(
            self.translation_model_path
        ):
            print("警告: 翻译模型路径不存在，跳过加载")
            return

        try:
            print(
                f"正在加载翻译模型: {self.translation_model_type} from {self.translation_model_path}"
            )

            if self.translation_model_type == "m2m100_418M":
                self.tokenizer = M2M100Tokenizer.from_pretrained(
                    self.translation_model_path
                )
                self.translation_model = M2M100ForConditionalGeneration.from_pretrained(
                    self.translation_model_path
                )
            elif self.translation_model_type == "nllb-200-3.3B":
                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.translation_model_path
                )
                self.translation_model = AutoModelForSeq2SeqLM.from_pretrained(
                    self.translation_model_path
                )
            else:
                print(f"警告: 不支持的模型类型 {self.translation_model_type}")
                return

            # 设置为评估模式
            self.translation_model.eval()
            print("翻译模型加载成功")

        except Exception as e:
            print(f"加载翻译模型失败: {str(e)}")
            self.translation_model = None
            self.tokenizer = None

    def _contains_chinese(self, text):
        """检查文本是否包含中文"""
        if not text:
            return False
        # 使用正则表达式匹配中文字符
        chinese_pattern = re.compile(r"[\u4e00-\u9fff]+")
        return bool(chinese_pattern.search(text))

    def _translate_chinese_to_english(self, text):
        """将中文文本翻译成英文"""
        if not self.translation_model or not self.tokenizer:
            print("警告: 翻译模型未加载，返回原文")
            return text

        if not self._contains_chinese(text):
            return text

        try:
            print(f"翻译中文文本: {text}")

            # 根据模型类型设置源语言和目标语言
            if self.translation_model_type == "m2m100_418M":
                # 设置中文到英文的翻译
                self.tokenizer.src_lang = "zh"
                encoded = self.tokenizer(
                    text, return_tensors="pt", padding=True, truncation=True
                )

                # 生成翻译
                with torch.no_grad():
                    generated_tokens = self.translation_model.generate(
                        **encoded, forced_bos_token_id=self.tokenizer.get_lang_id("en")
                    )

            elif self.translation_model_type == "nllb-200-3.3B":
                # NLLB模型使用语言代码
                encoded = self.tokenizer(
                    text, return_tensors="pt", padding=True, truncation=True
                )

                with torch.no_grad():
                    generated_tokens = self.translation_model.generate(
                        **encoded,
                        forced_bos_token_id=self.tokenizer.lang_code_to_id["eng_Latn"],
                    )
            else:
                return text

            # 解码翻译结果
            translated_text = self.tokenizer.decode(
                generated_tokens[0], skip_special_tokens=True
            )
            print(f"翻译结果: {translated_text}")
            return translated_text

        except Exception as e:
            print(f"翻译失败: {str(e)}，返回原文")
            return text

    def save_login_state(self):
        """保存登录状态到文件"""
        state_file = os.path.join(os.getcwd(), "user_data", "login_state.json")

        login_state = {
            "username": self.username,
            "user_info": self.user_info,
            "user_auth": self.user_auth,
            "saved_time": time.time(),
        }

        # 确保目录存在
        os.makedirs(os.path.dirname(state_file), exist_ok=True)

        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(login_state, f, ensure_ascii=False, indent=2)

        print(f"登录状态已保存到: {state_file}")

    def load_login_state(self):
        """从文件加载登录状态"""
        state_file = os.path.join(os.getcwd(), "user_data", "login_state.json")

        if not os.path.exists(state_file):
            print("未找到保存的登录状态文件")
            return False

        try:
            with open(state_file, "r", encoding="utf-8") as f:
                login_state = json.load(f)

            # 检查状态是否过期（7天有效期）
            if time.time() - login_state.get("saved_time", 0) > 7 * 24 * 3600:
                print("保存的登录状态已过期")
                return False

            # 检查用户名是否匹配
            if self.username and login_state.get("username") != self.username:
                print(
                    f"保存的登录状态用户名不匹配: 期望{self.username}, 实际{login_state.get('username')}"
                )
                return False

            # 应用登录状态
            self.user_info = login_state.get("user_info")
            self.user_auth = login_state.get("user_auth", {})

            # 设置localStorage中的认证信息（在正确上下文中执行）
            if self.user_auth.get("token"):
                # 确保在合适的页面上下文中设置localStorage
                try:
                    self.page.goto("https://www.fifedu.com")
                    self.page.wait_for_load_state("networkidle")
                    self.page.evaluate(
                        f"localStorage.setItem('Authorization', '{self.user_auth['token']}')"
                    )
                except Exception as e:
                    print(f"设置Authorization失败: {e}")

            if self.user_auth.get("source"):
                try:
                    self.page.evaluate(
                        f"localStorage.setItem('source', '{self.user_auth['source']}')"
                    )
                except Exception as e:
                    print(f"设置source失败: {e}")

            print("登录状态加载成功")
            return True

        except Exception as e:
            print(f"加载登录状态失败: {str(e)}")
            return False

    def login(self, username, password):
        """登录方法，支持多种认证模式"""
        self.username = username

        # 根据认证模式处理登录逻辑
        if self.auth_mode == "saved_only":
            # 仅使用保存的登录状态
            if self.load_login_state():
                # 验证登录状态是否有效
                try:
                    user_info = self.get_user_info()
                    print("使用保存的登录状态成功")
                    return user_info
                except Exception as e:
                    print(f"保存的登录状态无效: {str(e)}")
                    raise Exception("保存的登录状态无效，请使用其他认证模式重新登录")
            else:
                raise Exception("没有可用的保存登录状态")

        elif self.auth_mode == "auto":
            # 先尝试使用保存的登录状态
            if self.load_login_state():
                try:
                    user_info = self.get_user_info()
                    print("使用保存的登录状态成功")
                    return user_info
                except Exception as e:
                    print(f"保存的登录状态无效: {str(e)}，尝试重新登录")
                    # 继续执行登录流程

        # 需要重新登录的情况
        print("开始登录流程...")
        self.page.goto(self.urls["login"])

        # 清除可能的旧登录信息
        self.page.evaluate("localStorage.clear()")
        self.page.evaluate("sessionStorage.clear()")

        # 等待页面加载
        self.page.wait_for_load_state("networkidle")

        # 填写登录信息
        self.page.fill('input[name="user"]', username)
        self.page.fill('input[name="pass"]', password)
        self.page.get_by_role("button", name="登录").click()
        self.page.wait_for_load_state("networkidle")
        time.sleep(10)

        # 处理FiF口语训练系统弹窗
        with self.page.expect_popup() as fif_page:
            self.page.get_by_text("FiF口语训练系统", exact=True).click()
        page1 = fif_page.value
        page1.wait_for_load_state("networkidle")

        # 获取认证信息
        self.user_auth["token"] = page1.evaluate(
            "localStorage.getItem('Authorization')"
        )
        self.user_auth["source"] = page1.evaluate("localStorage.getItem('source')")
        page1.close()

        if self.user_auth["token"] is None or self.user_auth["token"] == "":
            raise Exception("登录失败")

        # 获取用户信息
        user_info = self.get_user_info()

        # 保存登录状态
        self.save_login_state()

        print("登录成功并保存状态")
        return user_info

    def get_user_info(self):
        if self.user_info is not None:
            return self.user_info
        else:
            response = self.page.request.fetch(
                self.api_urls["get_user_info"], method="GET"
            )
            if response.status != 200:
                raise Exception("获取用户信息失败")
            self.user_info = json.loads(response.body())
            return self.user_info

    def get_task_list(self, page):
        response = page.request.fetch(
            self.api_urls["get_task_list"],
            method="post",
            headers={
                "Authorization": "Bearer " + self.user_auth["token"],
                "source": self.user_auth["source"],
            },
            form={
                "userId": self.get_user_info()["data"]["userId"],
                "status": 1,
                "page": 1,
            },
        )
        json = response.json()
        if json["status"] == -1:
            raise Exception("获取任务列表失败")
        return json

    def get_ttd_list(self, page, task_id):
        response = page.request.fetch(
            self.api_urls["get_task_detail"],
            method="post",
            form={
                "userId": self.get_user_info()["data"]["userId"],
                "id": task_id,
            },
            headers={
                "Authorization": "Bearer " + self.user_auth["token"],
                "source": self.user_auth["source"],
            },
        )
        json = response.json()
        if json["status"] == -1:
            raise Exception("获取任务详情失败")
        return json

    def get_unit_info(self, page, unit_id, task_id):
        response = page.request.fetch(
            self.api_urls["get_unit_info"].format(unit_id, task_id),
            method="get",
            headers={
                "Authorization": "Bearer " + self.user_auth["token"],
                "source": self.user_auth["source"],
            },
        )
        json = response.json()
        if json["status"] == -1:
            raise Exception("获取单元信息失败")
        return json

    def start_level_test(self, page: Page, speaker, unit_id, task_id, level_id):
        print("尝试加载{}答案。".format(level_id))
        try:
            answer = self.get_level_answer(page, level_id)
            if answer != []:
                print("已加载{}条答案。".format(len(answer)))
                print(f"答案：{answer}")
        except Exception as e:
            raise Exception(f"加载答案失败: {str(e)}")

        # 获取关卡信息以判断是否为热身运动和题目类型
        level_info_response = page.request.fetch(
            self.api_urls["get_test_info"],
            method="post",
            form={
                "levelId": level_id,
            },
            headers={
                "Authorization": "Bearer " + self.user_auth["token"],
                "source": self.user_auth["source"],
            },
        ).json()

        if level_info_response["status"] != 1:
            raise Exception("获取关卡信息失败")

        level_name = level_info_response["data"]["levelName"]
        print(f"当前关卡名称: {level_name}")

        # 检查是否包含非录音题目（填空题、选择题、判断题）
        qcontent = [
            _i
            for _i in level_info_response["data"]["content"]["moshi"]
            if _i["name"] == "挑战"
        ][0]["question"]["qcontent"]

        has_non_recording_questions = False
        for item in qcontent["item"]:
            for question in item["questions"]:
                question_type = question.get("question_type", "")
                if question_type in ["1", "3", "6"]:  # 选择题、填空题、判断题
                    has_non_recording_questions = True
                    break
            if has_non_recording_questions:
                break

        page.goto(
            self.urls["unit_test"].format(
                self.get_user_info()["data"]["userId"],
                task_id,
                unit_id,
                level_id,
            )
        )

        page.wait_for_load_state("networkidle")

        page.frame_locator("iframe").get_by_role("tab", name="挑战").click()

        # 等待挑战页面加载完成
        page.wait_for_timeout(2000)

        # 根据关卡类型选择按钮
        if "热身" in level_name or "视听学习" in level_name:
            print(f"检测到非录音关卡 '{level_name}'，尝试点击'我知道啦！'按钮")
            try:
                # 首先尝试在主iframe中直接查找
                main_iframe = page.frame_locator("iframe")

                # 方法1: 直接在主iframe中查找按钮
                know_button = main_iframe.locator("button:has-text('我知道啦！')")
                if know_button.count() > 0 and know_button.is_visible():
                    know_button.click()
                    print("成功点击'我知道啦！'按钮（主iframe）")
                else:
                    # 方法2: 检查是否存在嵌套的iframe
                    nested_iframes = main_iframe.locator("iframe")
                    if nested_iframes.count() > 0:
                        print(
                            f"发现 {nested_iframes.count()} 个嵌套iframe，尝试在第一个中查找按钮"
                        )
                        nested_iframe = main_iframe.frame_locator("iframe")
                        know_button_nested = nested_iframe.locator(
                            "button:has-text('我知道啦！')"
                        )
                        if know_button_nested.count() > 0:
                            know_button_nested.click()
                            print("成功点击'我知道啦！'按钮（嵌套iframe）")
                        else:
                            # 方法3: 尝试在所有可能的iframe中查找
                            found = False
                            for i in range(nested_iframes.count()):
                                try:
                                    specific_iframe = main_iframe.frame_locator(
                                        f"iframe >> nth={i}"
                                    )
                                    button_in_specific = specific_iframe.locator(
                                        "button:has-text('我知道啦！')"
                                    )
                                    if button_in_specific.count() > 0:
                                        button_in_specific.click()
                                        print(
                                            f"成功点击'我知道啦！'按钮（第{i}个嵌套iframe）"
                                        )
                                        found = True
                                        break
                                except:
                                    continue
                            if not found:
                                raise Exception(
                                    "在所有嵌套iframe中都未找到'我知道啦！'按钮"
                                )
                    else:
                        # 方法4: 使用XPath定位（更精确）
                        xpath_button = main_iframe.locator(
                            "//button[contains(., '我知道啦！')]"
                        )
                        if xpath_button.count() > 0:
                            xpath_button.click()
                            print("成功点击'我知道啦！'按钮（XPath定位）")
                        else:
                            # 方法5: 尝试点击所有可能的按钮元素
                            all_buttons = main_iframe.locator("button")
                            clicked = False
                            for i in range(all_buttons.count()):
                                try:
                                    button_text = all_buttons.nth(i).text_content()
                                    if "我知道啦" in button_text:
                                        all_buttons.nth(i).click()
                                        print(
                                            f"成功点击'我知道啦！'按钮（遍历按钮文本，索引{i}）"
                                        )
                                        clicked = True
                                        break
                                except:
                                    continue
                            if not clicked:
                                raise Exception("无法找到包含'我知道啦'文本的按钮")
            except Exception as e:
                print(f"点击'我知道啦！'按钮失败: {str(e)}")
                # 调试信息：输出当前iframe中的所有按钮文本
                try:
                    main_iframe = page.frame_locator("iframe")
                    all_buttons = main_iframe.locator("button")
                    print(f"当前iframe中找到 {all_buttons.count()} 个按钮:")
                    for i in range(min(all_buttons.count(), 10)):  # 最多显示10个
                        try:
                            btn_text = all_buttons.nth(i).text_content().strip()
                            print(f"  按钮 {i}: '{btn_text}'")
                        except:
                            print(f"  按钮 {i}: 获取文本失败")
                except Exception as debug_e:
                    print(f"调试信息获取失败: {str(debug_e)}")
                raise Exception("无法点击'我知道啦！'按钮，请检查页面结构")
        else:
            print("普通关卡，点击'开始挑战'按钮")
            page.frame_locator("iframe").get_by_role("button", name="开始挑战").click()

        # 等待页面加载
        page.wait_for_timeout(3000)

        if has_non_recording_questions:
            print("检测到非录音题目，处理填空题、选择题、判断题")
            # 获取非录音题目的正确答案
            non_recording_answers = self.get_non_recording_answers(page, level_id)
            # 处理非录音题目
            self.handle_non_recording_questions(page, non_recording_answers)

            # 提交答案（如果有提交按钮）
            try:
                submit_button = page.frame_locator("iframe").get_by_role(
                    "button", name="提交"
                )
                if submit_button.is_visible():
                    submit_button.click()
                    print("已提交非录音题目答案")
            except:
                print("未找到提交按钮，可能自动提交")

            print("非录音题目处理完成。等待提交。")
            try:
                page.get_by_text("AI 评分").is_enabled(timeout=300000)  # 5分钟超时
            except Exception as e:
                raise Exception("等待提交超时（5分钟），可能页面卡死")
        else:
            # 原有的录音逻辑
            for answer_index, answer_text in enumerate(answer):
                print("等待开始录音。")
                try:
                    page.frame_locator("iframe").get_by_text("结束录音").is_enabled(
                        timeout=300000
                    )  # 5分钟超时
                except Exception as e:
                    raise Exception(
                        f"等待开始录音超时（5分钟），可能页面卡死。当前是第{answer_index + 1}条答案"
                    )

                print(
                    "正在回答第{}条。答案，内容为：\n{}".format(
                        answer_index + 1, answer_text
                    )
                )
                speaker.speak(answer_text)
                print("第{}条回答完成。".format(answer_index + 1))

                page.frame_locator("iframe").get_by_text("结束录音").click(force=True)

            print("挑战完成。等待提交。")
            try:
                page.get_by_text("AI 评分").is_enabled(timeout=300000)  # 5分钟超时
            except Exception as e:
                raise Exception("等待提交超时（5分钟），可能页面卡死")

        print("当前单元结束。")

    def get_level_answer(self, page: Page, level_id):
        """获取关卡答案，包含中文翻译功能"""
        response = page.request.fetch(
            self.api_urls["get_test_info"],
            method="post",
            form={
                "levelId": level_id,
            },
            headers={
                "Authorization": "Bearer " + self.user_auth["token"],
                "source": self.user_auth["source"],
            },
        ).json()
        if response["status"] != 1:
            raise Exception("获取答案失败")
        print(f"完整返回：{response}")
        qcontent = [
            _i for _i in response["data"]["content"]["moshi"] if _i["name"] == "挑战"
        ][0]["question"]["qcontent"]

        # 检查是否有任何问题有recordingTime字段，并且格式为#数字
        has_recording_time = False
        for item in qcontent["item"]:
            for question in item["questions"]:
                if "recordingTime" in question:
                    rt = question["recordingTime"].strip()
                    if rt and rt.startswith("#"):
                        has_recording_time = True
                        break
            if has_recording_time:
                break

        if has_recording_time:
            # 按照recordingTime分组答案
            answer_groups = {}
            for item in qcontent["item"]:
                for question in item["questions"]:
                    rt = question.get("recordingTime", "").strip()
                    if not rt or not rt.startswith("#"):
                        rt = "#1"  # 默认第一次录音
                    answer_text = question["title"]
                    # 清理答案文本：去除<...>标签
                    while answer_text.find("<") != -1:
                        answer_text = (
                            answer_text[: answer_text.find("<")]
                            + answer_text[answer_text.find(">") + 1 :]
                        )

                    # 翻译中文内容
                    if self.translation_model and self._contains_chinese(answer_text):
                        answer_text = self._translate_chinese_to_english(answer_text)

                    if rt not in answer_groups:
                        answer_groups[rt] = []
                    answer_groups[rt].append(answer_text)

            # 对分组进行排序，按照rt的数字顺序
            sorted_rt = sorted(
                answer_groups.keys(), key=lambda x: int(x[1:]) if x[1:].isdigit() else x
            )

            # 合并同一组的答案
            answers = []
            for rt in sorted_rt:
                group_answers = answer_groups[rt]
                combined_answer = " ".join(group_answers)
                answers.append(combined_answer)
            return answers
        else:
            # 没有recordingTime，按普通方式处理
            answer = []
            for _i in qcontent["item"]:
                for _j in _i["questions"]:
                    answer_text = _j["title"]
                    # 清理答案文本
                    while answer_text.find("<") != -1:
                        answer_text = (
                            answer_text[: answer_text.find("<")]
                            + answer_text[answer_text.find(">") + 1 :]
                        )

                    # 翻译中文内容
                    if self.translation_model and self._contains_chinese(answer_text):
                        answer_text = self._translate_chinese_to_english(answer_text)

                    answer.append(answer_text)
            return answer

    def get_playrole_type_answer(self, qcontent):
        """获取角色扮演类型答案，包含中文翻译功能"""
        answer = {}

        # 首先收集所有出现的角色
        all_roles = set()
        for _i in qcontent["item"]:
            for _j in _i["questions"]:
                if "photo" in _j:
                    all_roles.add(_j["photo"])

        # count role init - 修复初始化逻辑
        role_init_count = {}
        for role in all_roles:
            role_init_count[role] = 0

        for _i in qcontent["item"]:
            for _j in _i["questions"]:
                if "photo" not in _j:
                    continue

                role = _j["photo"]
                recording_time = _j.get("recordingTime", "").strip()

                if recording_time and "#" in recording_time:
                    try:
                        locate_part = recording_time.split("#")[0]
                        if locate_part:  # 确保不是空字符串
                            locate = int(locate_part)
                            # 更新最大位置计数
                            if locate > role_init_count[role]:
                                role_init_count[role] = locate
                    except (ValueError, IndexError):
                        # 忽略转换错误，使用当前位置计数
                        pass

        # 初始化每个角色的答案列表
        for role in all_roles:
            # 确保至少有1个位置（即使count为0）
            answer[role] = ["" for _ in range(max(1, role_init_count[role]))]

        # 填充答案
        for _i in qcontent["item"]:
            for _j in _i["questions"]:
                if "photo" not in _j:
                    continue

                role = _j["photo"]
                recording_time = _j.get("recordingTime", "").strip()

                if recording_time and "#" in recording_time:
                    try:
                        locate_part = recording_time.split("#")[0]
                        if locate_part:
                            locate = int(locate_part)
                        else:
                            locate = -1
                    except (ValueError, IndexError):
                        locate = -1
                else:
                    locate = -1

                answer_string = _j["title"]

                # remove string from '<' to '>' in answer_string
                while answer_string.find("<") != -1:
                    answer_string = (
                        answer_string[: answer_string.find("<")]
                        + answer_string[answer_string.find(">") + 1 :]
                    )

                # 翻译中文内容
                if self.translation_model and self._contains_chinese(answer_string):
                    answer_string = self._translate_chinese_to_english(answer_string)

                if locate != -1 and locate <= len(answer[role]):
                    # 确保索引有效
                    answer[role][locate - 1] += answer_string
                else:
                    # 如果位置无效或超出范围，添加到列表末尾
                    answer[role].append(answer_string)

        # 构建最终结果，增加健壮性检查
        result = []
        sample = qcontent.get("sample", "").split("#")

        # 如果sample为空，使用所有角色
        if sample == [""]:
            sample = list(all_roles)

        print(f"调试信息 - 样本角色: {sample}")
        print(f"调试信息 - 答案字典中的角色: {list(answer.keys())}")

        for role in sample:
            # 确保角色存在于answer字典中
            if role in answer:
                for answer_string in answer[role]:
                    if answer_string.strip():  # 只添加非空答案
                        result.append(answer_string)
            else:
                print(f"警告: 角色 '{role}' 在答案数据中不存在，已跳过")

        # 如果结果为空，尝试从所有角色收集答案
        if not result:
            print("从sample构建结果为空，尝试从所有角色收集答案")
            for role in all_roles:
                for answer_string in answer[role]:
                    if answer_string.strip():
                        result.append(answer_string)

        print(f"最终收集到 {len(result)} 条答案")
        return result

    def get_page(self):
        return self.page

    def get_context(self):
        return self.context

    def get_browser(self):
        return self.browser

    def get_playwright(self):
        return self.playwright

    def get_url(self):
        return self.url

    def save_storage_state(self):
        """保存当前会话的存储状态到用户数据目录"""
        user_data_dir = os.path.join(os.getcwd(), "user_data")
        storage_state_path = os.path.join(user_data_dir, "storage_state.json")

        # 确保目录存在
        if not os.path.exists(user_data_dir):
            os.makedirs(user_data_dir)

        # 保存存储状态
        storage_state = self.context.storage_state()
        with open(storage_state_path, "w") as f:
            json.dump(storage_state, f)
        print(f"已保存存储状态到: {storage_state_path}")

    def clear_login_state(self):
        """清除保存的登录状态"""
        state_file = os.path.join(os.getcwd(), "user_data", "login_state.json")
        if os.path.exists(state_file):
            os.remove(state_file)
            print("已清除保存的登录状态")
        else:
            print("没有找到保存的登录状态文件")

    def get_non_recording_answers(self, page: Page, level_id):
        """获取非录音题的答案（填空题、选择题、判断题、匹配题）"""
        response = page.request.fetch(
            self.api_urls["get_test_info"],
            method="post",
            form={
                "levelId": level_id,
            },
            headers={
                "Authorization": "Bearer " + self.user_auth["token"],
                "source": self.user_auth["source"],
            },
        ).json()
        if response["status"] != 1:
            raise Exception("获取答案失败")

        qcontent = [
            _i for _i in response["data"]["content"]["moshi"] if _i["name"] == "挑战"
        ][0]["question"]["qcontent"]

        questions = []
        for item in qcontent["item"]:
            for question in item["questions"]:
                # 提取题目信息
                question_info = {
                    "title": question.get("title", ""),
                    "question_type": question.get("question_type", ""),
                    "right_answer": question.get("right_answer", []),
                    "sub_question_id": question.get("sub_question_id", ""),
                }

                # 对于匹配题，额外提取选项信息
                if question.get("question_type") == "7":
                    question_info["answer"] = question.get("answer", [])

                # 清理题目文本
                title_text = question_info["title"]
                while title_text.find("<") != -1:
                    title_text = (
                        title_text[: title_text.find("<")]
                        + title_text[title_text.find(">") + 1 :]
                    )
                question_info["clean_title"] = title_text

                questions.append(question_info)

        return questions

    def handle_non_recording_questions(self, page: Page, questions_data):
        """处理非录音题（填空题、选择题、判断题、匹配题），基于API顺序和ti_container索引建立正确映射"""
        import random

        # 首先确定正确的iframe上下文
        main_iframe = page.frame_locator("iframe")

        # 检查是否存在嵌套iframe
        nested_iframes = main_iframe.locator("iframe")
        if nested_iframes.count() > 0:
            print(f"检测到 {nested_iframes.count()} 个嵌套iframe，使用第一个进行操作")
            target_iframe = main_iframe.frame_locator("iframe")
        else:
            print("未检测到嵌套iframe，使用主iframe进行操作")
            target_iframe = main_iframe

        # 等待页面加载完成
        page.wait_for_timeout(1000)

        # 分析实际的ti_container结构来确定正确的索引映射
        ti_containers = target_iframe.locator(".ti_container")
        total_ti_containers = ti_containers.count()
        print(f"检测到 {total_ti_containers} 个ti_container元素")

        # 统计各种题型的数量以建立正确的映射
        fill_in_blanks = []  # 填空题
        multiple_choice = []  # 选择题
        true_false = []  # 判断题
        matching = []  # 匹配题

        for question in questions_data:
            if question["question_type"] == "3":
                fill_in_blanks.append(question)
            elif question["question_type"] == "1":
                multiple_choice.append(question)
            elif question["question_type"] == "6":
                true_false.append(question)
            elif question["question_type"] == "7":
                matching.append(question)

        print(
            f"题目统计 - 填空题: {len(fill_in_blanks)}, 选择题: {len(multiple_choice)}, 判断题: {len(true_false)}, 匹配题: {len(matching)}"
        )

        # 处理填空题（通常只在第一页）
        if fill_in_blanks:
            # 收集所有填空题的答案，保持原有顺序
            all_answers = []
            for question in fill_in_blanks:
                all_answers.extend(question["right_answer"])

            if all_answers:
                try:
                    # 查找所有contentInput span元素
                    all_spans = target_iframe.locator("span.contentInput")
                    span_count = all_spans.count()

                    print(
                        f"找到 {span_count} 个填空题输入框，需要填写 {len(all_answers)} 个答案"
                    )

                    if span_count == 0:
                        print("警告: 未找到任何填空题输入框")
                    else:
                        # 按顺序填写答案到对应的输入框
                        for j in range(min(len(all_answers), span_count)):
                            answer = all_answers[j]
                            try:
                                span_element = all_spans.nth(j)
                                # 获取span的ID用于日志
                                span_id = (
                                    span_element.get_attribute("id")
                                    or f"unknown_id_{j}"
                                )

                                # 点击span元素获得焦点
                                span_element.click()
                                # 输入答案
                                page.keyboard.type(answer)
                                print(
                                    f"成功填写填空题 第 {j+1} 空 ({span_id}): {answer}"
                                )

                                # 点击底部弹出的完成按钮来保存答案
                                try:
                                    # 等待弹出面板出现（最多2秒）
                                    page.wait_for_timeout(500)

                                    # 查找完成按钮 - 在footBoxInput容器内的em元素
                                    complete_button = target_iframe.locator(
                                        "#footBoxInput em:has-text('完成')"
                                    )
                                    if complete_button.count() > 0:
                                        complete_button.click()
                                        print(f"成功点击填空题 第 {j+1} 空的完成按钮")
                                    else:
                                        # 备用方案：直接查找包含"完成"文本的em元素
                                        complete_button_alt = target_iframe.locator(
                                            "em:has-text('完成')"
                                        )
                                        found_button = False
                                        for k in range(complete_button_alt.count()):
                                            try:
                                                btn_text = (
                                                    complete_button_alt.nth(k)
                                                    .text_content()
                                                    .strip()
                                                )
                                                if btn_text == "完成":
                                                    complete_button_alt.nth(k).click()
                                                    print(
                                                        f"成功点击填空题 第 {j+1} 空的完成按钮（备用方案）"
                                                    )
                                                    found_button = True
                                                    break
                                            except:
                                                continue

                                        if not found_button:
                                            # 再次备用：查找所有em元素
                                            all_em = target_iframe.locator("em")
                                            for k in range(all_em.count()):
                                                try:
                                                    em_text = (
                                                        all_em.nth(k)
                                                        .text_content()
                                                        .strip()
                                                    )
                                                    if em_text == "完成":
                                                        all_em.nth(k).click()
                                                        print(
                                                            f"成功点击填空题 第 {j+1} 空的完成按钮（遍历em）"
                                                        )
                                                        found_button = True
                                                        break
                                                except:
                                                    continue

                                            if not found_button:
                                                print(
                                                    f"警告: 未找到填空题 第 {j+1} 空的完成按钮"
                                                )

                                except Exception as complete_e:
                                    print(
                                        f"点击填空题完成按钮时发生异常: {str(complete_e)}"
                                    )

                            except Exception as e:
                                print(f"填写填空题 第 {j+1} 空失败: {str(e)}")

                            # 随机等待0.5-1秒
                            page.wait_for_timeout(random.randint(500, 1000))

                        # 警告信息
                        if len(all_answers) > span_count:
                            print(
                                f"警告: 答案数量({len(all_answers)})多于输入框数量({span_count})"
                            )
                        elif span_count > len(all_answers):
                            print(
                                f"警告: 输入框数量({span_count})多于答案数量({len(all_answers)})"
                            )
                except Exception as e:
                    print(f"处理填空题时发生错误: {str(e)}")
            else:
                print("没有填空题答案需要填写")

        # 处理选择题和判断题和匹配题（按ti_container的实际顺序，使用CSS类名识别题型）
        mc_index = 0  # 选择题索引（在multiple_choice列表中的位置）
        tf_index = 0  # 判断题索引（在true_false列表中的位置）
        match_index = 0  # 匹配题索引（在matching列表中的位置）

        # 记录已处理的题目索引
        processed_mc_indices = []
        processed_tf_indices = []
        processed_match_indices = []

        for ti_index in range(total_ti_containers):
            try:
                # 获取当前ti_container的标题用于调试
                try:
                    title_element = target_iframe.locator(
                        f".ti_container:nth-child({ti_index + 1}) .question-title"
                    )
                    if title_element.count() > 0:
                        title_text = title_element.first.text_content().strip()
                        print(f"ti_container {ti_index + 1} 标题: {title_text[:50]}...")
                    else:
                        content_element = target_iframe.locator(
                            f".ti_container:nth-child({ti_index + 1}) p"
                        )
                        if content_element.count() > 0:
                            content_text = content_element.first.text_content().strip()
                            print(
                                f"ti_container {ti_index + 1} 内容预览: {content_text[:50]}..."
                            )
                except:
                    pass

                # 判断题型（通过CSS类名和实际选项存在性）
                blue_elements = target_iframe.locator(
                    f".ti_container:nth-child({ti_index + 1}) .blue"
                )
                green_elements = target_iframe.locator(
                    f".ti_container:nth-child({ti_index + 1}) .green"
                )

                # 检查是否有实际的选项元素
                radio_labels = target_iframe.locator(
                    f".ti_container:nth-child({ti_index + 1}) .van-radio__label"
                )
                has_radio_options = radio_labels.count() > 0

                # 检查是否是匹配题（通常有select下拉框或特定的匹配UI）
                select_elements = target_iframe.locator(
                    f".ti_container:nth-child({ti_index + 1}) select"
                )
                match_options = target_iframe.locator(
                    f".ti_container:nth-child({ti_index + 1}) .match-option"
                )
                # 匹配题可能表现为表格形式
                table_rows = target_iframe.locator(
                    f".ti_container:nth-child({ti_index + 1}) table tr, .ti_container:nth-child({ti_index + 1}) .table-row"
                )
                # 或者每行有一个van-radio-group
                radio_groups = target_iframe.locator(
                    f".ti_container:nth-child({ti_index + 1}) .van-radio-group"
                )

                # 判断是否为匹配题：有多行，每行有选项，或者有表格结构
                is_matching = (
                    select_elements.count() > 0
                    or match_options.count() > 0
                    or (
                        radio_groups.count() > 1 and len(matching) > match_index
                    )  # 多个单选组可能是匹配题
                    or (
                        table_rows.count() > 1 and len(matching) > match_index
                    )  # 表格形式
                )

                is_multiple_choice = (
                    blue_elements.count() > 0
                    and "单选题" in blue_elements.first.text_content()
                ) or (
                    has_radio_options
                    and not is_matching
                    and len(multiple_choice) > mc_index
                )
                is_true_false = green_elements.count() > 0

                # 调试输出
                print(
                    f"ti_container {ti_index + 1}: blue={blue_elements.count()}, green={green_elements.count()}, radio={radio_labels.count()}, select={select_elements.count()}, radio_groups={radio_groups.count()}, table_rows={table_rows.count()}"
                )

                if blue_elements.count() > 0:
                    try:
                        blue_text = blue_elements.first.text_content().strip()
                        print(f"  .blue 元素文本: '{blue_text}'")
                    except:
                        pass
                if green_elements.count() > 0:
                    try:
                        green_text = green_elements.first.text_content().strip()
                        print(f"  .green 元素文本: '{green_text}'")
                    except:
                        pass

                if is_multiple_choice and mc_index < len(multiple_choice):
                    # 处理选择题
                    question = multiple_choice[mc_index]
                    answer_choice = (
                        question["right_answer"][0] if question["right_answer"] else ""
                    )

                    if answer_choice:
                        try:
                            # 先输出所有可用选项用于调试
                            try:
                                option_count = radio_labels.count()
                                print(
                                    f"ti_container {ti_index + 1} 可用选项数量: {option_count}"
                                )
                                for opt_idx in range(option_count):
                                    try:
                                        opt_em = radio_labels.nth(opt_idx).locator("em")
                                        if opt_em.count() > 0:
                                            opt_text = (
                                                opt_em.first.text_content().strip()
                                            )
                                            print(f"  选项 {opt_idx + 1}: '{opt_text}'")
                                    except:
                                        pass

                                # 如果没有找到选项，尝试其他可能的选择器
                                if option_count == 0:
                                    print(
                                        f"ti_container {ti_index + 1} 尝试其他选择器..."
                                    )
                                    # 尝试直接查找em元素
                                    direct_em = target_iframe.locator(
                                        f".ti_container:nth-child({ti_index + 1}) em"
                                    )
                                    em_count = direct_em.count()
                                    print(f"  直接em元素数量: {em_count}")
                                    for em_idx in range(em_count):
                                        try:
                                            em_text = (
                                                direct_em.nth(em_idx)
                                                .text_content()
                                                .strip()
                                            )
                                            print(f"    em {em_idx + 1}: '{em_text}'")
                                        except:
                                            pass

                            except Exception as debug_e:
                                print(f"选项调试信息获取失败: {str(debug_e)}")

                            # 直接点击包含答案选项的label（添加超时）
                            option_selector = f".ti_container:nth-child({ti_index + 1}) .van-radio__label:has(em:text-is('{answer_choice}'))"
                            target_iframe.locator(option_selector).click(timeout=5000)
                            print(
                                f"成功选择选择题 {mc_index + 1} (ti_container {ti_index + 1}): {answer_choice}"
                            )
                        except Exception as e:
                            try:
                                # 备用：点击em元素（添加超时）
                                em_selector = f".ti_container:nth-child({ti_index + 1}) em:text-is('{answer_choice}')"
                                target_iframe.locator(em_selector).click(timeout=5000)
                                print(
                                    f"成功选择选择题 {mc_index + 1} (点击em): {answer_choice}"
                                )
                            except Exception as e2:
                                # 再次备用：点击包含答案的任何元素
                                try:
                                    any_selector = f".ti_container:nth-child({ti_index + 1}) :text-is('{answer_choice}')"
                                    target_iframe.locator(any_selector).click(
                                        timeout=5000
                                    )
                                    print(
                                        f"成功选择选择题 {mc_index + 1} (点击任意包含答案的元素): {answer_choice}"
                                    )
                                except Exception as e3:
                                    # 遍历所有选项（添加超时）
                                    try:
                                        selected = False
                                        for k in range(radio_labels.count()):
                                            try:
                                                option_em = radio_labels.nth(k).locator(
                                                    "em"
                                                )
                                                if option_em.count() > 0:
                                                    em_text = (
                                                        option_em.first.text_content().strip()
                                                    )
                                                    if em_text == answer_choice:
                                                        radio_labels.nth(k).click(
                                                            timeout=5000
                                                        )
                                                        print(
                                                            f"成功选择选择题 {mc_index + 1} (遍历em): {answer_choice}"
                                                        )
                                                        selected = True
                                                        break
                                            except:
                                                continue
                                        if not selected:
                                            print(
                                                f"选择题 {mc_index + 1} 选择失败: 所有方法都失败，目标答案: '{answer_choice}'"
                                            )
                                    except Exception as e4:
                                        print(
                                            f"选择题 {mc_index + 1} 选择失败: {str(e4)}"
                                        )

                    processed_mc_indices.append(mc_index)
                    mc_index += 1

                elif is_true_false and tf_index < len(true_false):
                    # 处理判断题
                    question = true_false[tf_index]
                    answer_bool = (
                        question["right_answer"][0] if question["right_answer"] else ""
                    )

                    if answer_bool:
                        try:
                            if answer_bool == "TRUE":
                                selector = f".ti_container:nth-child({ti_index + 1}) .radio_panduan .van-radio__label:has-text('TRUE')"
                                target_iframe.locator(selector).click(timeout=5000)
                                print(
                                    f"成功选择判断题 {tf_index + 1} (ti_container {ti_index + 1}): TRUE"
                                )
                            else:
                                selector = f".ti_container:nth-child({ti_index + 1}) .radio_panduan .van-radio__label:has-text('FALSE')"
                                target_iframe.locator(selector).click(timeout=5000)
                                print(
                                    f"成功选择判断题 {tf_index + 1} (ti_container {ti_index + 1}): FALSE"
                                )
                        except Exception as e:
                            try:
                                # 直接点击文本
                                if answer_bool == "TRUE":
                                    text_selector = f".ti_container:nth-child({ti_index + 1}) .radio_panduan :text-is('TRUE')"
                                    target_iframe.locator(text_selector).click(
                                        timeout=5000
                                    )
                                    print(
                                        f"成功选择判断题 {tf_index + 1} (点击TRUE文本): TRUE"
                                    )
                                else:
                                    text_selector = f".ti_container:nth-child({ti_index + 1}) .radio_panduan :text-is('FALSE')"
                                    target_iframe.locator(text_selector).click(
                                        timeout=5000
                                    )
                                    print(
                                        f"成功选择判断题 {tf_index + 1} (点击FALSE文本): FALSE"
                                    )
                            except Exception as e2:
                                # 遍历判断题选项
                                try:
                                    radio_group = target_iframe.locator(
                                        f".ti_container:nth-child({ti_index + 1}) .radio_panduan"
                                    )
                                    options = radio_group.locator(".van-radio__label")
                                    selected = False
                                    for k in range(options.count()):
                                        try:
                                            option_text = (
                                                options.nth(k).text_content().strip()
                                            )
                                            if answer_bool in option_text:
                                                options.nth(k).click(timeout=5000)
                                                print(
                                                    f"成功选择判断题 {tf_index + 1} (遍历): {answer_bool}"
                                                )
                                                selected = True
                                                break
                                        except:
                                            continue
                                    if not selected:
                                        print(
                                            f"判断题 {tf_index + 1} 选择失败: 所有方法都失败"
                                        )
                                except Exception as e3:
                                    print(f"判断题 {tf_index + 1} 选择失败: {str(e3)}")

                    processed_tf_indices.append(tf_index)
                    tf_index += 1

                elif is_matching and match_index < len(matching):
                    # 处理匹配题
                    question = matching[match_index]
                    right_answers = question.get("right_answer", [])
                    answer_data = question.get("answer", [])

                    print(
                        f"处理匹配题 {match_index + 1}，共 {len(right_answers)} 个匹配项"
                    )

                    # 获取选项列表
                    left_options = []
                    right_options = []
                    if len(answer_data) >= 2:
                        left_choise_list = answer_data[0].get("choise_list", [])
                        right_choise_list = answer_data[1].get("choise_list", [])

                        for item in left_choise_list:
                            left_options.append(
                                {
                                    "name": str(item.get("choise_name", "")),
                                    "title": item.get("title", ""),
                                }
                            )

                        for item in right_choise_list:
                            right_options.append(
                                {
                                    "name": str(item.get("choise_name", "")),
                                    "title": item.get("title", ""),
                                }
                            )

                    print(f"  左侧选项: {[opt['name'] for opt in left_options]}")
                    print(f"  右侧选项: {[opt['name'] for opt in right_options]}")
                    print(f"  正确答案: {right_answers}")

                    # 尝试多种方式处理匹配题
                    try:
                        # 方法1: 检查是否有select下拉框
                        select_elements = target_iframe.locator(
                            f".ti_container:nth-child({ti_index + 1}) select"
                        )
                        if select_elements.count() > 0:
                            print(f"  检测到 {select_elements.count()} 个下拉框")
                            # 按顺序设置每个下拉框的值
                            for i, answer in enumerate(right_answers):
                                if i < select_elements.count():
                                    try:
                                        select_element = select_elements.nth(i)
                                        # 使用select_option选择值
                                        select_element.select_option(
                                            value=answer, timeout=5000
                                        )
                                        print(f"  成功设置匹配题第 {i+1} 行: {answer}")
                                    except Exception as e:
                                        print(f"  设置匹配题第 {i+1} 行失败: {str(e)}")

                        # 方法2: 检查是否有匹配行的单选按钮组
                        else:
                            # 尝试查找匹配行
                            match_rows = target_iframe.locator(
                                f".ti_container:nth-child({ti_index + 1}) .match-row, .ti_container:nth-child({ti_index + 1}) tr, .ti_container:nth-child({ti_index + 1}) .row"
                            )
                            if match_rows.count() > 0:
                                print(f"  检测到 {match_rows.count()} 个匹配行")
                                for i, answer in enumerate(right_answers):
                                    if i < match_rows.count():
                                        try:
                                            row = match_rows.nth(i)
                                            # 在行内查找对应的单选按钮
                                            radio = row.locator(
                                                f"input[type='radio'][value='{answer}'], .van-radio:has-text('{answer}')"
                                            )
                                            if radio.count() > 0:
                                                radio.first.click(timeout=5000)
                                                print(
                                                    f"  成功选择匹配题第 {i+1} 行: {answer}"
                                                )
                                            else:
                                                # 尝试点击包含答案文本的元素
                                                label = row.locator(
                                                    f"label:has-text('{answer}'), span:has-text('{answer}')"
                                                )
                                                if label.count() > 0:
                                                    label.first.click(timeout=5000)
                                                    print(
                                                        f"  成功点击匹配题第 {i+1} 行文本: {answer}"
                                                    )
                                        except Exception as e:
                                            print(
                                                f"  处理匹配题第 {i+1} 行失败: {str(e)}"
                                            )

                            # 方法3: 遍历所有单选按钮组
                            else:
                                print("  尝试遍历单选按钮组...")
                                radio_groups = target_iframe.locator(
                                    f".ti_container:nth-child({ti_index + 1}) .van-radio-group"
                                )
                                if radio_groups.count() > 0:
                                    for i, answer in enumerate(right_answers):
                                        if i < radio_groups.count():
                                            try:
                                                group = radio_groups.nth(i)
                                                # 在组内查找对应的选项
                                                option = group.locator(
                                                    f".van-radio__label:has-text('{answer}'), label:has-text('{answer}')"
                                                )
                                                if option.count() > 0:
                                                    option.first.click(timeout=5000)
                                                    print(
                                                        f"  成功选择匹配题第 {i+1} 组: {answer}"
                                                    )
                                            except Exception as e:
                                                print(
                                                    f"  处理匹配题第 {i+1} 组失败: {str(e)}"
                                                )
                                else:
                                    # 方法4: 直接查找包含答案的所有可点击元素
                                    print("  尝试直接查找可点击元素...")
                                    for i, answer in enumerate(right_answers):
                                        try:
                                            # 查找所有包含答案的元素
                                            elements = target_iframe.locator(
                                                f".ti_container:nth-child({ti_index + 1}) :text-is('{answer}')"
                                            )
                                            if elements.count() > 0:
                                                # 点击第i个匹配的元素（假设按顺序排列）
                                                elements.nth(
                                                    min(i, elements.count() - 1)
                                                ).click(timeout=5000)
                                                print(f"  成功点击匹配题答案: {answer}")
                                        except Exception as e:
                                            print(
                                                f"  点击匹配题答案 {answer} 失败: {str(e)}"
                                            )

                    except Exception as e:
                        print(f"处理匹配题失败: {str(e)}")

                    processed_match_indices.append(match_index)
                    match_index += 1

                else:
                    # 调试：记录未处理的ti_container
                    print(
                        f"ti_container {ti_index + 1}: 未识别为选择题、判断题或匹配题，跳过"
                    )

            except Exception as e:
                print(f"处理ti_container {ti_index + 1} 时出错: {str(e)}")

            # 随机等待0.5-1秒
            page.wait_for_timeout(random.randint(500, 1000))

        # 输出最终处理统计
        print(
            f"最终处理结果 - 选择题: {mc_index}, 判断题: {tf_index}, 匹配题: {match_index}"
        )
        if mc_index < len(multiple_choice):
            print(f"警告: 有 {len(multiple_choice) - mc_index} 个选择题未处理")
        if tf_index < len(true_false):
            print(f"警告: 有 {len(true_false) - tf_index} 个判断题未处理")
        if match_index < len(matching):
            print(f"警告: 有 {len(matching) - match_index} 个匹配题未处理")

        # 输出所有题目的正确答案
        print("\n=== 所有题目的正确答案 ===")

        # 输出填空题答案
        if fill_in_blanks:
            print("填空题答案:")
            for i, question in enumerate(fill_in_blanks):
                clean_title = question.get("clean_title", "未知题目")
                answers = question.get("right_answer", [])
                print(f"  填空题 {i+1}: {clean_title[:50]}... -> 答案: {answers}")

        # 输出选择题答案
        if multiple_choice:
            print("选择题答案:")
            for i, question in enumerate(multiple_choice):
                clean_title = question.get("clean_title", "未知题目")
                answers = question.get("right_answer", [])
                status = "✓ 已处理" if i in processed_mc_indices else "✗ 未处理"
                print(
                    f"  选择题 {i+1}: {clean_title[:50]}... -> 答案: {answers} {status}"
                )

        # 输出判断题答案
        if true_false:
            print("判断题答案:")
            for i, question in enumerate(true_false):
                clean_title = question.get("clean_title", "未知题目")
                answers = question.get("right_answer", [])
                status = "✓ 已处理" if i in processed_tf_indices else "✗ 未处理"
                print(
                    f"  判断题 {i+1}: {clean_title[:50]}... -> 答案: {answers} {status}"
                )

        # 输出匹配题答案
        if matching:
            print("匹配题答案:")
            for i, question in enumerate(matching):
                clean_title = question.get("clean_title", "未知题目")
                answers = question.get("right_answer", [])
                status = "✓ 已处理" if i in processed_match_indices else "✗ 未处理"
                print(
                    f"  匹配题 {i+1}: {clean_title[:50]}... -> 答案: {answers} {status}"
                )

        # 特别输出未处理的题目答案
        unprocessed_questions = []
        for i, question in enumerate(multiple_choice):
            if i not in processed_mc_indices:
                unprocessed_questions.append(("选择题", i + 1, question))
        for i, question in enumerate(true_false):
            if i not in processed_tf_indices:
                unprocessed_questions.append(("判断题", i + 1, question))
        for i, question in enumerate(matching):
            if i not in processed_match_indices:
                unprocessed_questions.append(("匹配题", i + 1, question))

        if unprocessed_questions:
            print("\n=== 未处理题目的详细答案 ===")
            for q_type, q_num, question in unprocessed_questions:
                clean_title = question.get("clean_title", "未知题目")
                answers = question.get("right_answer", [])
                print(f"{q_type} {q_num}: {clean_title}")
                print(f"  正确答案: {answers}")
                if q_type == "匹配题":
                    answer_data = question.get("answer", [])
                    if len(answer_data) >= 2:
                        left_choise_list = answer_data[0].get("choise_list", [])
                        right_choise_list = answer_data[1].get("choise_list", [])
                        print(
                            f"  左侧选项: {[item.get('title', '') for item in left_choise_list]}"
                        )
                        print(
                            f"  右侧选项: {[item.get('title', '') for item in right_choise_list]}"
                        )
