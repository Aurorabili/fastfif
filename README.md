<!-- @format -->

<div align="center">
    <h1 align="center">Fast FiF</h1>
    <p align="center">使用生成语音全自动完成FiF英语口语作业</p>
</div>

# 🎯 目标

任何人都有自己学习和练习英语口语的方式，特别是对于大学生来说，强制要求他们学习不感兴趣的语言和采用作业的形式评价他们的学习成果显然是十分糟糕的。大学生们通常有自己清晰的目标。时间应该被利用在更需要的地方。

本项目是针对于[FiF口语训练系统](https://www.fifedu.com/iplat/html/home/home.html)的自动完成脚本。旨在使用非侵入式的方法自动完成口语作业。

# 🌟 特性

- **IndexTTS 1.5**模型只需要数秒即可模仿你的声音，支持 GPU/CPU 运行。

- 模拟点击而非网络包中间人攻击，FiF口语难以检测你的行为。

- 打开浏览器也是自动的。全程只需你一次点击。

- 使用虚拟麦克风输入，它将安静的在后台工作。

- **跨平台支持**：现已支持 Windows 和 Linux 平台。

- **智能控分**：支持单词丢弃程度和复杂度配置，实现精准分数控制。

- **自动填写填空题**：程序可自动识别并填写填空选择题（需手动提交，但程序会把答案输出供你修改审查）。

- **中英文智能翻译**：自动检测中文答案并翻译为英文后再进行语音合成（支持 M2M100 和 NLLB 模型）。

- **浏览器配置持久化**：一次登录后可复用登录状态，虚拟麦克风设置也会被记住。

- **自动恢复机制**：遇到无响应或登录失效时自动重启程序（最多重试20次，可自己配置）。

- **随机User-Agent池**：多种浏览器User-Agent轮换。

- **静音播放**：浏览器自动静音，避免干扰用户。

- **多用户支持**：支持多个用户配置，每个用户可使用独立的样本声音文件。

# 🍗 使用

**现已支持 Windows 和 Linux 平台！**

## 驱动依赖

### Windows 平台

- **虚拟麦克风**：需要安装 VB-Audio Virtual Cable 驱动
  - 下载地址：https://vb-audio.com/Cable/
  - 安装后会创建 "CABLE Input (VB-Audio Virtual Cable)" 设备
- **浏览器驱动**：Playwright 会自动下载所需的 Microsoft Edge 浏览器驱动

### Linux 平台

项目使用`pulseaudio`来创建虚拟麦克风。

```bash
pulseaudio      # Linux声卡驱动
```

可以使用提供的脚本快速创建虚拟麦克风：

```bash
bash scripts/create_virtualpipemic.sh
```

## 克隆项目到本地

```bash
git clone https://github.com/Aurorabili/fastfif
cd fastfif
```

## 建议使用conda安装项目依赖，indextts 依赖的安装建议参考indextts官方库

```bash
conda env create -f environment.yml
```

## 填写FiF口语用户名和密码

在项目根目录创建`user.json`:

```json
{
  "username": "你的FiF口语用户名",
  "password": "你的FiF口语密码",
  "drop_level": 0.2,
  "complexity": 5,
  "use_gpu": true
}
```

**配置说明：**

- `drop_level`：单词丢弃程度（0-1），用于控制分数，默认 0.2
  - 0 表示不丢弃任何单词
  - 1 表示丢弃所有长难单词
  - 建议值：0.1-0.3
- `complexity`：长难单词复杂度（最小字符数），默认 5
  - 只有长度大于等于此值的单词才会被考虑丢弃
  - 建议值：5-8
- `use_gpu`：是否使用 GPU 运行 IndexTTS，默认 true（需 CUDA 支持）
  - true：使用 GPU 加速（需要 NVIDIA 显卡和 CUDA）
  - false：使用 CPU 运行（速度较慢但兼容性更好）

## 录制样本声音

IndexTTS 1.5 需要一段10秒左右的录音来模仿你的音色以生成口语作业里的英语录音。你可以在安静的环境中使用手机录音机进行录音。然后重命名并放到这个路径`draft/target_voice.wav`。这个录音需要你朗读一段英文文本，大概在10秒钟左右，请在安静的地方进行以确保没有底噪。

这里提供一段英文文本：

```
The original vision of AI was re-articulated in two sousands via the term Artificial General Intelligence or AGI. This vision is to build Thinking Machines computer systems that can learn, reason, and solve problems similar to the way humans do.
```

**多用户支持：**

你可以在 `draft/` 目录下创建多个子文件夹，为不同用户存放不同的样本声音文件。例如：

```
draft/
├── target_voice.wav          # 默认用户样本
├── user1/
│   └── target_voice.wav      # 用户1的样本
├── user2/
│   └── target_voice.wav      # 用户2的样本
└── user3/
    └── target_voice.wav      # 用户3的样本
```

程序会自动根据用户名选择对应的样本声音文件。

## 启动项目

当一切准备就绪。使用python运行`src/main.py`。

```bash
python src/main.py
```

**首次运行说明：**

1. 程序会自动启动 IndexTTS API 服务器（需要10-15秒启动时间）
2. 程序会初始化浏览器配置（首次需要手动登录）
3. 登录信息和虚拟麦克风设置会被保存到 `user_data/` 目录，下次启动可直接使用
4. 程序遇到无响应或登录失效会自动重启（最多重试20次）
5. 填空选择题会自动填写，但需要手动提交
6. 多选题和类似题型会在控制台输出正确答案供参考

**自动恢复机制：**

程序内置了强大的自动恢复机制：

- 当检测到登录失效或网络错误时，会自动清理登录状态并重启
- 最多自动重启20次，避免无限循环
- 每次重启前会等待5秒，给系统缓冲时间
- 重启次数会显示在控制台输出中

**运行日志：**

程序会输出详细的运行日志，包括：

- API服务器启动状态
- 浏览器操作状态
- 语音合成进度
- 题目处理情况
- 错误和警告信息

# 🗺️ 路线图

- [x] 使用其他虚拟麦克风方案以支持在Windows平台部署。
- [x] 升级到 IndexTTS 1.5 模型。
- [x] 添加单词丢弃和复杂度控制功能。
- [x] 添加中英文翻译功能。
- [x] 添加浏览器配置持久化功能。
- [x] 添加自动恢复机制。
- [x] 添加随机User-Agent池。
- [x] 添加多用户支持。
- [ ] 一键部署脚本，方便任何人立刻开始他的FiF口语之旅。
- [ ] 添加Android版本FiF客户端连接器。
- [ ] 使用原音输出或在线TTS降低算力要求以支持边缘计算平台。
- [ ] 支持快速微调的模型以拟真声音。
- [ ] 完善多选题和几选几题型的自动填写功能。

# 😞 已知问题

- 在作业`四六级口语,六级口语模拟题 2,Part 2-1-1 个人发言`(levelid:e22e45aaeaf64e42ace1fa5ea038d2b0)中的第二题里FiF口语会在3秒后自动结束录音导致无法完成作业。
- 多选题和类似几选几的题型程序无法自动填写，但会在控制台输出正确答案供手动填写参考。
- 首次启动 IndexTTS API 服务器可能需要较长时间（约10-15秒）。
- Windows平台需要手动安装VB-Audio Virtual Cable驱动。
- 翻译模型需要额外下载和配置（M2M100或NLLB模型）。

# 🪜 代码结构

```
src
├── main.py             # 主程序，包含自动重启机制和API服务器管理
├── connector           # FiF客户端连接器
│   ├── FiFWebClient.py # 核心连接器，包含登录、任务获取、题目处理等功能
│   └── __init__.py
├── speaker             # 语音合成器抽象
│   ├── Speaker.py      # 语音合成器接口
│   └── __init__.py
├── tts                 # TTS模型（IndexTTS 1.5）
│   ├── TTSSolver.py    # TTS求解器，包含文本处理和API调用
│   └── __init__.py
├── vmic                # 虚拟麦克风实现
│   ├── VirtualMic.py   # Linux虚拟麦克风实现
│   ├── WindowsVirtualMic.py # Windows虚拟麦克风实现
│   └── __init__.py
├── draft               # 样本声音文件目录
│   ├── target_voice.wav
│   └── [用户名]/       # 多用户样本声音
├── user_data           # 用户数据和浏览器配置（持久化）
│   ├── login_state.json # 登录状态缓存
│   └── Default/        # 浏览器数据
├── tmp                 # 临时音频文件目录
└── user.json           # 用户配置文件

scripts/
└── create_virtualpipemic.sh  # Linux虚拟麦克风创建脚本
```

## 核心模块说明

### main.py

- 主程序入口
- 管理IndexTTS API服务器进程
- 实现自动重启机制（最多20次）\- 异常处理和清理逻辑

### connector/FiFWebClient.py

- 使用Playwright自动化浏览器操作
- 实现登录、任务获取、题目处理等核心功能
- 支持多种认证模式（auto、force_login、saved_only）
- 集成中英文翻译功能（M2M100/NLLB模型）
- 随机User-Agent池，提高反检测能力
- 浏览器配置持久化

### speaker/Speaker.py

- 语音合成器抽象接口
- 根据平台选择虚拟麦克风实现
- 支持动态调整丢弃程度和复杂度

### tts/TTSSolver.py

- IndexTTS 1.5模型集成
- 文本预处理（随机丢弃长难单词）
- API调用和音频文件生成

### vmic/

- VirtualMic.py：Linux平台使用pulseaudio创建虚拟麦克风
- WindowsVirtualMic.py：Windows平台使用VB-Cable虚拟麦克风

# 🎈 提交贡献

我一个人无法和日益更新的FiF口语系统抗衡。受限于我自己的口语作业，我也无法适配所有题目类型。

我们欢迎任何人提交贡献。如果你有任何想法、建议、新题型以及错误报告，欢迎提交issue，我们很期待与你讨论。如果你有任何代码上的改进，欢迎提交PR。

# 📝 说明

本项目仅供学习交流使用，不得用于商业用途。使用本项目造成的一切后果由使用者自行承担。

# 🔗 引用

- [microsoft/playwright](https://github.com/microsoft/playwright) - 浏览器自动化框架
- [IndexTTS](https://github.com/index-tts/index-tts) - 语音合成模型
- [transformers](https://github.com/huggingface/transformers) - 翻译模型支持
- [M2M100](https://huggingface.co/facebook/m2m100_418M) - 多语言翻译模型
- [NLLB](https://huggingface.co/facebook/nllb-200-3.3B) - 多语言翻译模型
- [VB-Audio Virtual Cable](https://vb-audio.com/Cable/) - Windows虚拟麦克风驱动
- [sounddevice](https://python-sounddevice.readthedocs.io/) - Python音频处理库
- [soundfile](https://pysoundfile.readthedocs.io/) - Python音频文件处理库

# 📜 许可证

本项目使用[MIT许可证](LICENSE)。
