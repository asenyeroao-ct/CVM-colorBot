<div align="center">
  <img src="cvm.jpg" alt="CVM-colorBot Logo" width="200"/>
  
  # CVM-colorBot
  
  [![Discord](https://img.shields.io/badge/Discord-Join%20Server-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/WVjNThUb56)
</div>

CVM colorbot is a computer-vision mouse aiming system using HSV color detection with MAKCU hardware. Supports NDI, UDP, and Capture Card input, offering customizable sensitivity, smoothing, FOV settings, and anti-smoke filtering for precise 2-PC aiming workflows.

## Features

### Core Modules
- **Aimbot**: Intelligent targeting system with multiple modes (head/body/nearest)
- **Triggerbot**: Automated trigger with burst firing and cooldown management
- **RCS (Recoil Control System)**: Automatic recoil compensation
- **Anti-Smoke Detection**: Advanced filtering to avoid targeting through smoke

### Video Capture Support
- **NDI**: Network Device Interface for streaming video sources
- **UDP**: High-speed UDP video streaming
- **Capture Card**: Direct capture card input support

### Hardware Integration
- **MAKCU USB Device**: High-speed mouse control via serial communication
- **Multi-Device Support**: Compatible with MAKCU, CH343, CH340, CH347, and CP2102
- **High-Speed Communication**: Configurable baud rates up to 4Mbps

### Customization Options
- Adjustable sensitivity and smoothing
- Configurable FOV (Field of View) settings
- Granular display and overlay controls
- Real-time performance monitoring

## Requirements

### Hardware
- **MAKCU USB Device** (or compatible serial adapter: CH343, CH340, CH347, CP2102)
- Windows 10/11
- USB port for MAKCU connection

### Software
- Python 3.12+
- Windows operating system

## Installation

### Method 1: Quick Setup (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/asenyeroao-ct/CVM-colorBot.git
   cd CVM-colorBot
   ```

2. **Run the setup script**
   ```bash
   setup.bat
   ```
   This will automatically:
   - Check Python installation
   - Create a virtual environment
   - Install all dependencies

3. **Run the application**
   ```bash
   run.bat
   ```

### Method 2: Manual Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/asenyeroao-ct/CVM-colorBot.git
   cd CVM-colorBot
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python main.py
   ```
   
   Or use the provided batch file:
   ```bash
   run.bat
   ```

## Usage

### Initial Setup

1. **Connect MAKCU Device**
   - Plug in your MAKCU USB device
   - The application will automatically detect and connect

2. **Configure Video Source**
   - Select capture method: NDI, UDP, or Capture Card
   - Configure connection settings based on your selected method
   - Click "CONNECT" to establish connection

3. **Adjust Settings**
   - Navigate through tabs: General, Aimbot, Sec Aimbot, Trigger, RCS, Config
   - Configure sensitivity, smoothing, FOV, and other parameters
   - Settings are automatically saved to `config.json`

### Configuration Tabs

- **General**: Capture controls, sensitivity, operation mode, target color
- **Aimbot**: Main aiming settings, sensitivity, FOV, offsets, targeting mode
- **Sec Aimbot**: Secondary aimbot configuration
- **Trigger**: Triggerbot settings, delay, hold, burst controls
- **RCS**: Recoil control system parameters
- **Config**: Save/load configuration profiles

## Project Structure

```
CVM-colorBot/
├── main.py                 # Main application entry point
├── requirements.txt        # Python dependencies
├── config.json            # Application configuration
├── run.bat                # Windows launcher
├── setup.bat              # Setup script
├── src/
│   ├── ui.py              # GUI interface (CustomTkinter)
│   ├── aim_system/        # Aiming system modules
│   │   ├── normal.py      # Normal mode aimbot
│   │   ├── silent.py      # Silent mode aimbot
│   │   ├── Triggerbot.py  # Triggerbot logic
│   │   ├── RCS.py         # Recoil control system
│   │   └── anti_smoke_detector.py
│   ├── capture/           # Video capture modules
│   │   ├── capture_service.py
│   │   ├── ndi.py         # NDI capture
│   │   ├── CaptureCard.py # Capture card support
│   │   └── OBS_UDP.pyx    # UDP streaming
│   └── utils/             # Utility modules
│       ├── config.py      # Configuration management
│       ├── detection.py   # HSV color detection
│       └── mouse.py       # MAKCU mouse control
├── configs/               # Configuration profiles
└── themes/                # UI themes
```

## Configuration

Configuration is stored in `config.json` and can be managed through the GUI or manually edited. Key settings include:

- **Capture Settings**: Video source, resolution, FPS
- **Aimbot Settings**: Sensitivity, smoothing, FOV, targeting mode
- **Triggerbot Settings**: Delay, hold time, burst count, cooldown
- **RCS Settings**: Pull speed, activation delay, rapid click threshold
- **Display Settings**: OpenCV windows, overlay elements

## Supported Devices

### Serial Adapters
- MAKCU (1A86:55D3)
- CH343 (1A86:5523)
- CH340 (1A86:7523)
- CH347 (1A86:5740)
- CP2102 (10C4:EA60)

### Video Sources
- NDI sources (via Network Device Interface)
- UDP video streams
- Capture cards (via DirectShow/Media Foundation)

## Technical Details

- **Color Detection**: HSV-based color space detection for target identification
- **Mouse Control**: High-speed serial communication via MAKCU device
- **Video Processing**: OpenCV for real-time frame processing
- **GUI Framework**: CustomTkinter for modern, customizable interface
- **Multi-threading**: Asynchronous processing for smooth performance

## License

Copyright (c) 2025 asenyeroao-ct. All rights reserved.

This project is licensed under a custom license. See [LICENSE](LICENSE) file for details.

**Key Points:**
- Personal, non-commercial use is permitted
- Modification and redistribution are allowed with proper attribution
- Commercial use is prohibited without written permission
- Original author **asenyeroao-ct** must be credited in all distributions

## Disclaimer

This software is provided for educational and research purposes only. Users are responsible for ensuring compliance with applicable laws and terms of service of any software or games used with this tool.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

- **Discord**: [Join our Discord server](https://discord.gg/WVjNThUb56) for community support, discussions, and updates
- **GitHub Issues**: For bug reports, questions, or feature requests, please open an issue on [GitHub](https://github.com/asenyeroao-ct/CVM-colorBot/issues)

