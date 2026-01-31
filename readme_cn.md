<div align="center">
  <img src="cvm.jpg" alt="CVM-colorBot Logo" width="200"/>
  
  # CVM-colorBot
  
  [![Discord](https://img.shields.io/badge/Discord-加入服务器-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/WVjNThUb56)
</div>

CVM colorbot 是一个基于计算机视觉的鼠标瞄准系统，使用 HSV 颜色检测技术，配合 MAKCU 硬件。支持 NDI、UDP 和采集卡输入，提供可自定义的灵敏度、平滑度、FOV 设置和反烟雾过滤功能，适用于精确的双 PC 瞄准工作流程。

## 功能特性

### 核心模块
- **Aimbot（自瞄）**：智能瞄准系统，支持多种模式（头部/身体/最近目标）
- **Triggerbot（扳机）**：自动扳机，支持连发和冷却管理
- **RCS（后坐力控制系统）**：自动后坐力补偿
- **反烟雾检测**：高级过滤功能，避免瞄准烟雾中的目标

### 视频采集支持
- **NDI**：网络设备接口，用于流式视频源
- **UDP**：高速 UDP 视频流
- **采集卡**：直接采集卡输入支持

### 硬件集成
- **MAKCU USB 设备**：通过串口通信实现高速鼠标控制
- **多设备支持**：兼容 MAKCU、CH343、CH340、CH347 和 CP2102
- **高速通信**：可配置波特率，最高 4Mbps

### 自定义选项
- 可调节的灵敏度和平滑度
- 可配置的 FOV（视野）设置
- 精细的显示和叠加控制
- 实时性能监控

## 系统要求

### 硬件
- **MAKCU USB 设备**（或兼容的串口适配器：CH343、CH340、CH347、CP2102）
- Windows 10/11
- USB 端口用于连接 MAKCU

### 软件
- Python 3.12+
- Windows 操作系统

## 安装

### 方法 1：快速安装（推荐）

1. **克隆仓库**
   ```bash
   git clone https://github.com/asenyeroao-ct/CVM-colorBot.git
   cd CVM-colorBot
   ```

2. **运行安装脚本**
   ```bash
   setup.bat
   ```
   这将自动：
   - 检查 Python 安装
   - 创建虚拟环境
   - 安装所有依赖项

3. **运行应用程序**
   ```bash
   run.bat
   ```

### 方法 2：手动安装

1. **克隆仓库**
   ```bash
   git clone https://github.com/asenyeroao-ct/CVM-colorBot.git
   cd CVM-colorBot
   ```

2. **创建虚拟环境**（推荐）
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **安装依赖项**
   ```bash
   pip install -r requirements.txt
   ```

4. **运行应用程序**
   ```bash
   python main.py
   ```
   
   或使用提供的批处理文件：
   ```bash
   run.bat
   ```

## 使用说明

### 初始设置

1. **连接 MAKCU 设备**
   - 插入您的 MAKCU USB 设备
   - 应用程序将自动检测并连接

2. **配置视频源**
   - 选择采集方法：NDI、UDP 或采集卡
   - 根据您选择的方法配置连接设置
   - 点击 "CONNECT" 建立连接

3. **调整设置**
   - 浏览各个标签页：General、Aimbot、Sec Aimbot、Trigger、RCS、Config
   - 配置灵敏度、平滑度、FOV 和其他参数
   - 设置会自动保存到 `config.json`

### 配置标签页

- **General（常规）**：采集控制、灵敏度、操作模式、目标颜色
- **Aimbot（自瞄）**：主要瞄准设置、灵敏度、FOV、偏移量、瞄准模式
- **Sec Aimbot（次要自瞄）**：次要自瞄配置
- **Trigger（扳机）**：扳机设置、延迟、保持时间、连发控制
- **RCS**：后坐力控制系统参数
- **Config（配置）**：保存/加载配置配置文件

## 项目结构

```
CVM-colorBot/
├── main.py                 # 主应用程序入口点
├── requirements.txt        # Python 依赖项
├── config.json            # 应用程序配置
├── run.bat                # Windows 启动器
├── setup.bat              # 安装脚本
├── src/
│   ├── ui.py              # GUI 界面（CustomTkinter）
│   ├── aim_system/        # 瞄准系统模块
│   │   ├── normal.py      # 普通模式自瞄
│   │   ├── silent.py      # 静默模式自瞄
│   │   ├── Triggerbot.py  # 扳机逻辑
│   │   ├── RCS.py         # 后坐力控制系统
│   │   └── anti_smoke_detector.py
│   ├── capture/           # 视频采集模块
│   │   ├── capture_service.py
│   │   ├── ndi.py         # NDI 采集
│   │   ├── CaptureCard.py # 采集卡支持
│   │   └── OBS_UDP.pyx    # UDP 流
│   └── utils/             # 工具模块
│       ├── config.py      # 配置管理
│       ├── detection.py   # HSV 颜色检测
│       └── mouse.py       # MAKCU 鼠标控制
├── configs/               # 配置配置文件
└── themes/                # UI 主题
```

## 配置

配置存储在 `config.json` 中，可以通过 GUI 或手动编辑进行管理。主要设置包括：

- **采集设置**：视频源、分辨率、FPS
- **自瞄设置**：灵敏度、平滑度、FOV、瞄准模式
- **扳机设置**：延迟、保持时间、连发次数、冷却时间
- **RCS 设置**：拉枪速度、激活延迟、快速点击阈值
- **显示设置**：OpenCV 窗口、叠加元素

## 支持的设备

### 串口适配器
- MAKCU (1A86:55D3)
- CH343 (1A86:5523)
- CH340 (1A86:7523)
- CH347 (1A86:5740)
- CP2102 (10C4:EA60)

### 视频源
- NDI 源（通过网络设备接口）
- UDP 视频流
- 采集卡（通过 DirectShow/Media Foundation）

## 技术细节

- **颜色检测**：基于 HSV 颜色空间的目标识别
- **鼠标控制**：通过 MAKCU 设备进行高速串口通信
- **视频处理**：使用 OpenCV 进行实时帧处理
- **GUI 框架**：使用 CustomTkinter 构建现代化、可自定义的界面
- **多线程**：异步处理以确保流畅性能

## 许可证

版权所有 (c) 2025 asenyeroao-ct。保留所有权利。

本项目采用自定义许可证。详情请参阅 [LICENSE](LICENSE) 文件。

**要点：**
- 允许个人、非商业用途
- 允许修改和重新分发，但需正确署名
- 未经书面许可禁止商业用途
- 所有分发版本必须标注原作者 **asenyeroao-ct**

## 免责声明

本软件仅供教育和研究用途。用户需自行确保遵守相关法律法规以及使用本工具的任何软件或游戏的服务条款。

## 贡献

欢迎贡献！请随时提交 Pull Request。

## 支持

- **Discord**：加入我们的 [Discord 服务器](https://discord.gg/WVjNThUb56) 获取社区支持、讨论和更新
- **GitHub Issues**：如需报告错误、提问或功能请求，请在 [GitHub](https://github.com/asenyeroao-ct/CVM-colorBot/issues) 上提交 issue

