# Repository Guidelines

## Project Overview

CVM-colorBot is a Windows-first Python application that provides computer-vision-based mouse aiming assistance using HSV color detection. The system supports multiple video capture backends (NDI, UDP, Capture Card, MSS) and integrates with MAKCU hardware for high-speed mouse control. The application features a CustomTkinter-based GUI for configuration and real-time monitoring.

**Key Technologies:**
- Python 3.x (Windows only)
- CustomTkinter for GUI
- OpenCV for image processing
- NumPy for numerical operations
- PySerial for serial communication
- MSS for screen capture

## Project Structure & Module Organization

The app is a Windows-first Python project with `main.py` as the entry point. Core code lives under `src/`:

### Entry Point
- `main.py`: Main application entry point. Initializes `AimTracker`, `CaptureService`, and `ViewerApp`. Handles application lifecycle and threading.

### Core Modules

#### `src/ui.py`
- **Purpose**: CustomTkinter-based GUI interface
- **Key Classes**: `ViewerApp` (main window)
- **Features**: 
  - Tabbed interface (General, Aimbot, Sec Aimbot, Trigger, RCS, Config)
  - Real-time configuration management
  - Capture connection controls
  - Settings persistence via `config.json`

#### `src/aim_system/`
Aiming system modules implementing different targeting modes and features:
- `normal.py`: Normal mode aimbot with smooth tracking
- `silent.py`: Silent mode aimbot with delayed movement
- `NCAF.py`: Near-Center Aiming Feature with snap radius logic
- `Bezier.py`: Bezier curve-based smooth movement
- `windmouse_smooth.py`: WindMouse algorithm implementation
- `Triggerbot.py`: Automated trigger system with burst firing support
- `RCS.py`: Recoil Control System for automatic recoil compensation
- `anti_smoke_detector.py`: Advanced filtering to avoid targeting through smoke

#### `src/capture/`
Video capture backends for different input sources:
- `capture_service.py`: Unified capture service interface
- `ndi.py`: Network Device Interface (NDI) video streaming support
- `OBS_UDP.py`: UDP video streaming (OBS-compatible)
- `CaptureCard.py`: DirectShow/Media Foundation capture card support
- `mss_capture.py`: MSS (Multiple Screen Shot) screen capture backend

#### `src/utils/`
Utility modules for configuration, detection, and hardware integration:
- `config.py`: Configuration management (`Config` class, JSON persistence)
- `detection.py`: HSV color detection and model loading
- `debug_logger.py`: Debug logging utilities
- `updater.py`: Application update checking
- `activation.py`: License/activation management
- `mouse_input.py`: Mouse input handling utilities
- `mouse/`: Mouse API implementations
  - `SerialAPI.py`: Serial port communication (MAKCU, CH343, CH340, CH347, CP2102)
  - `ArduinoAPI.py`: Arduino-compatible serial communication
  - `SendInputAPI.py`: Windows SendInput API for mouse control
  - `NetAPI.py`: Network-based mouse control (via DLL)
  - `MakV2.py`: MakV2 device support
  - `DHZAPI.py`: DHZ device support
  - `state.py`: Mouse state management

### Configuration & Data Files
- `config.json`: Runtime configuration (tracked in repository)
- `configs/default.json`: Default profile template (tracked)
- `configs/*`: User profiles (ignored by git, except `default.json`)
- `themes/`: UI theme files (JSON format)
  - `metal.json`: Metal theme
  - `midnight.json`: Midnight theme
- `version.json`: Application version information

### Build & Scripts
- `setup.bat`: Automated setup script (creates venv, installs dependencies)
- `run.bat`: Application launcher (uses venv Python)
- `requirements.txt`: Python dependencies
- `update.ps1`: PowerShell update script

## Build, Test, and Development Commands

### Initial Setup
1. **Automated Setup (Recommended)**
   ```bash
   setup.bat
   ```
   This script:
   - Checks Python installation
   - Creates virtual environment (`venv/`)
   - Upgrades pip
   - Installs all dependencies from `requirements.txt`

2. **Manual Setup**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

### Running the Application
- **Using launcher script** (recommended):
  ```bash
  run.bat
  ```
  - Automatically uses `venv\Scripts\python.exe`
  - Checks for virtual environment before running

- **Direct execution** (after venv activation):
  ```bash
  venv\Scripts\activate
  python main.py
  ```

### Development Commands
- **Syntax check** (before PR):
  ```bash
  python -m compileall main.py src
  ```
  
- **Check Python version**:
  ```bash
  python --version
  ```
  Verify Python is installed and accessible.

- **Update dependencies**:
  ```bash
  venv\Scripts\activate
  pip install --upgrade -r requirements.txt
  ```

- **Clean build artifacts**:
  ```bash
  # Remove __pycache__ directories
  for /d /r . %d in (__pycache__) do @if exist "%d" rd /s /q "%d"
  # Remove .pyc files
  del /s /q *.pyc
  ```

### Key Dependencies
- `customtkinter==5.2.2`: Modern GUI framework
- `numpy==2.2.6`: Numerical operations
- `opencv-python==4.12.0.88`: Image processing and video capture
- `cyndilib==0.0.8`: NDI library
- `pyserial==3.5`: Serial communication
- `requests>=2.31.0`: HTTP requests (for updates)
- `Pillow>=10.0.0`: Image processing
- `mss>=9.0.0`: Screen capture

## Coding Style & Naming Conventions

### General Guidelines
- **Indentation**: 4 spaces (no tabs)
- **Line length**: Prefer 100 characters or less (soft limit)
- **Spacing**: Follow PEP 8 style guide
- **Imports**: Group imports (stdlib, third-party, local) with blank lines between groups

### Naming Conventions
- **Functions and variables**: `snake_case`
  ```python
  def calculate_aim_offset():
      target_distance = 100.0
  ```

- **Classes**: `PascalCase`
  ```python
  class AimTracker:
      def __init__(self):
          pass
  ```

- **Constants**: `UPPER_SNAKE_CASE`
  ```python
  MAX_FPS = 1000
  DEFAULT_SENSITIVITY = 0.5
  ```

- **Private methods/attributes**: Leading underscore `_private_method()`
  ```python
  def _process_move_queue(self):
      self._internal_state = True
  ```

- **Config keys**: `snake_case` (must match `config.json` and `src/utils/config.py`)
  ```python
  self.normal_x_speed = getattr(config, "normal_x_speed", 0.5)
  ```

### Code Organization
- **Module structure**: 
  - Imports at top
  - Constants
  - Classes
  - Helper functions
  - `if __name__ == "__main__":` block (if applicable)

- **Class structure**:
  - `__init__` method first
  - Public methods
  - Private methods (prefixed with `_`)
  - Properties and descriptors

### Legacy Code Compatibility
- Some legacy modules use non-standard naming (e.g., `Triggerbot.py`, `RCS.py`)
- **Do not rename** existing files unless part of a dedicated refactoring PR
- Follow existing conventions when modifying legacy code
- New modules should follow `snake_case` naming

### Documentation
- Use docstrings for classes and public methods (Google style or NumPy style)
- Add inline comments for complex logic
- Document configuration parameters in `src/utils/config.py`
- **Comments should use Traditional Chinese and English mixed**: Code comments (inline comments and docstrings) should use a mix of Traditional Chinese and English. This allows for better readability for both Chinese and English-speaking developers while maintaining clarity.

### Documentation & UI Guidelines
- **Update documentation when updating information**: When making changes to features, configuration options, or functionality, ensure that the corresponding documentation in `docs/` is updated accordingly
- **Update both Chinese and English documentation versions**: When updating documentation files in `docs/`, both the Chinese (`zh-CN`) and English (`en`) versions must be updated simultaneously. Ensure that the content and structure remain consistent across both language versions.
- **UI text must be in English only**: All user-facing text in the UI (labels, buttons, tooltips, error messages, etc.) must be written in English. Do not use other languages in UI elements

### Example Code Style
```python
class ExampleClass:
    """Example class demonstrating code style."""
    
    def __init__(self, config_value: float = 0.5):
        """Initialize example class.
        
        Args:
            config_value: Configuration value with default.
        """
        self._internal_state = False
        self.config_value = config_value
    
    def public_method(self, param: int) -> bool:
        """Public method with type hints.
        
        Args:
            param: Integer parameter.
            
        Returns:
            Boolean result.
        """
        return self._private_helper(param) > 0
    
    def _private_helper(self, value: int) -> int:
        """Private helper method."""
        return value * 2
```

## Testing Guidelines

### Current Testing Status
There is currently no committed automated test suite. Manual testing is required for all changes.

### Manual Testing Checklist
For each change, verify the following:

1. **Application Startup**
   - Run `run.bat` (or `python main.py`)
   - Verify UI loads without errors
   - Check console for error messages

2. **Core Functionality**
   - **Capture Connection**: Test all capture backends (NDI, UDP, Capture Card, MSS)
   - **Aimbot Modes**: Test Normal, Silent, NCAF, WindMouse, Bezier modes
   - **Triggerbot**: Verify trigger behavior, burst firing, cooldown
   - **RCS**: Test recoil compensation activation and behavior
   - **Config Management**: Save/load profiles, verify persistence

3. **Mouse API Integration**
   - Test all supported mouse APIs (Serial, Arduino, SendInput, Net, MakV2, DHZ)
   - Verify connection and movement commands
   - Test button masking functionality

4. **UI Functionality**
   - Verify all tabs load correctly
   - Test configuration changes are reflected immediately
   - Check OpenCV windows display (if enabled)
   - Verify theme switching

5. **Edge Cases**
   - Test with no capture source connected
   - Test with invalid configuration values
   - Test rapid configuration changes
   - Test application close/restart

### Adding Automated Tests
If adding testable logic, create pytest tests:

- **Location**: `tests/` directory
- **Naming**: `test_<module>.py` (e.g., `test_config.py`, `test_detection.py`)
- **Structure**:
  ```python
  import pytest
  from src.utils.config import Config
  
  def test_config_defaults():
      """Test default configuration values."""
      config = Config()
      assert config.enableaim is True
      assert config.mode == "Normal"
  ```

- **Running tests**:
  ```bash
  venv\Scripts\activate
  pip install pytest
  pytest tests/
  ```

### Testing Specific Features

#### Capture Backends
- **NDI**: Requires NDI source available on network
- **UDP**: Requires UDP stream on configured port
- **Capture Card**: Requires capture card hardware
- **MSS**: Should work on any Windows system

#### Aimbot Modes
- **Normal**: Smooth tracking with configurable speed
- **Silent**: Delayed movement with return-to-center
- **NCAF**: Snap radius and near radius behavior
- **WindMouse**: Human-like mouse movement
- **Bezier**: Curve-based smooth movement

#### Configuration Testing
- Test default values load correctly
- Test custom values persist after restart
- Test profile save/load functionality
- Test invalid values are handled gracefully

## Version Management

### Version Number Format

The project uses **Semantic Versioning** with the format `a.b.c` (Major.Minor.Patch):

- **`a` (Major version)**: Incremented for major version releases
  - Breaking changes that are not backward compatible
  - Significant architectural changes
  - Major feature additions that fundamentally change the application
  - Examples: Complete UI redesign, new core system architecture, removal of deprecated features

- **`b` (Minor version)**: Incremented for minor version releases
  - New features that are backward compatible
  - New capture backends, aimbot modes, or mouse APIs
  - New configuration options
  - UI enhancements and improvements
  - Examples: Adding NCAF mode, new capture backend support, new theme options

- **`c` (Patch version)**: Incremented for patch/bugfix releases
  - Bug fixes that don't add new features
  - Performance improvements
  - Code refactoring that doesn't change behavior
  - Documentation updates
  - Examples: Fixing triggerbot cooldown bug, improving capture stability, fixing config save issues

### Version Number Rules

1. **Version numbers are numeric only**: Use integers (e.g., `1.0.0`, `2.5.3`, `10.15.7`)
2. **Start from 1.0.0**: Initial release should be `1.0.0` or higher
3. **Reset lower numbers**: When incrementing a higher number, reset lower numbers to 0
   - Example: `1.5.3` → `2.0.0` (major bump)
   - Example: `1.5.3` → `1.6.0` (minor bump)
   - Example: `1.5.3` → `1.5.4` (patch bump)
4. **Always update version on release**: Every release (PR merge to main) must update the version number

### Version File Location

Version information is stored in `version.json`:

```json
{
    "version": "1.0.0",
    "release_date": "2025-01-20",
    "changelog": "Initial release with update system"
}
```

### When to Update Version

#### Update Major Version (`a`)
- Breaking changes to configuration structure (requires migration)
- Removal of deprecated features or APIs
- Major architectural refactoring
- Changes that require users to reconfigure their setup

#### Update Minor Version (`b`)
- Adding new features (new aimbot modes, capture backends, mouse APIs)
- Adding new configuration options
- UI enhancements and new themes
- Performance improvements that add new capabilities
- Any backward-compatible feature addition

#### Update Patch Version (`c`)
- Bug fixes for existing features
- Performance optimizations (without new features)
- Code cleanup and refactoring
- Documentation improvements
- Fixing crashes or stability issues

### Version Update Workflow

1. **Before creating PR**:
   - Determine the appropriate version bump based on changes
   - Update `version.json` with new version number
   - Update `release_date` to the planned release date (or current date)
   - Update `changelog` with a brief description of changes

2. **When pushing to GitHub**:
   - **Always update `version.json` before pushing commits to GitHub**
   - Ensure the version number reflects all changes in the commit
   - Update `release_date` to the current date (or planned release date)
   - Write a clear and concise `changelog` that summarizes the changes
   - The `version.json` file is used by the update checker system to notify users of new versions
   - **Never push changes without updating the version number** if the changes include:
     - New features
     - Bug fixes
     - Performance improvements
     - Configuration changes
     - UI updates
     - Documentation updates (may be patch version)

3. **Version update example**:
   ```json
   {
       "version": "1.2.0",
       "release_date": "2025-01-25",
       "changelog": "Added MSS capture backend support and improved NDI stability"
   }
   ```

4. **In PR description**:
   - Include version number in PR title or description: `[v1.2.0] Add MSS capture backend`
   - Document version bump type (major/minor/patch) in PR description
   - Mention that `version.json` has been updated

5. **After PR merge**:
   - Verify `version.json` is updated correctly on the main branch
   - Tag the release if creating a release (optional but recommended)
   - The update checker will automatically detect the new version from GitHub

### Version Update Examples

#### Example 1: Bug Fix (Patch)
**Before**: `1.0.0`  
**After**: `1.0.1`  
**Reason**: Fixed triggerbot burst firing cooldown calculation bug

```json
{
    "version": "1.0.1",
    "release_date": "2025-01-21",
    "changelog": "Fixed triggerbot burst firing cooldown calculation"
}
```

#### Example 2: New Feature (Minor)
**Before**: `1.0.1`  
**After**: `1.1.0`  
**Reason**: Added new WindMouse aimbot mode

```json
{
    "version": "1.1.0",
    "release_date": "2025-01-22",
    "changelog": "Added WindMouse aimbot mode with human-like movement patterns"
}
```

#### Example 3: Breaking Change (Major)
**Before**: `1.5.3`  
**After**: `2.0.0`  
**Reason**: Refactored configuration structure, removed deprecated config options

```json
{
    "version": "2.0.0",
    "release_date": "2025-02-01",
    "changelog": "Major refactor: Updated configuration structure. Migration guide available in docs."
}
```

#### Example 4: Multiple Changes (Minor)
**Before**: `1.2.0`  
**After**: `1.3.0`  
**Reason**: Added new theme and improved UI responsiveness

```json
{
    "version": "1.3.0",
    "release_date": "2025-01-28",
    "changelog": "Added midnight theme and improved UI responsiveness"
}
```

### Version in Code

If the application needs to access version information programmatically:

```python
import json
from pathlib import Path

def get_version():
    """Get application version from version.json."""
    version_file = Path(__file__).parent.parent / "version.json"
    with open(version_file, 'r') as f:
        version_data = json.load(f)
    return version_data["version"]
```

### Version Best Practices

1. **One version per release**: Don't skip version numbers (e.g., don't go from `1.0.0` to `1.0.3` if `1.0.1` and `1.0.2` weren't released)
2. **Consistent formatting**: Always use three-part version numbers (`a.b.c`)
3. **Meaningful changelog**: Write clear, concise changelog entries that describe what changed
4. **Update on merge**: Version should be updated in the same PR that introduces the changes
5. **Document breaking changes**: For major version bumps, document migration steps in PR description or docs

### Version and Release Tags

When creating Git tags for releases:
- Use version number as tag: `v1.2.0` (with `v` prefix)
- Tag format: `v{version}` (e.g., `v1.0.0`, `v2.5.3`)
- Tag the commit that merges the PR with version update

## Commit & Pull Request Guidelines

### Commit Message Format
**備註：所有 commit 訊息必須使用英文撰寫。**

Use short, imperative subjects following conventional commit style:

**Good examples:**
- `Update capture service to support MSS backend`
- `Fix: Triggerbot burst firing cooldown calculation`
- `Add NCAF mode support for secondary aimbot`
- `Refactor: Extract mouse API interface to base class`
- `Fix: Config save/load race condition`

**Bad examples:**
- `fixed some bugs` (too vague)
- `changes` (not descriptive)
- `WIP` (incomplete work)
- `asdf` (meaningless)

### Commit Structure
- **Subject line**: 50 characters or less, imperative mood
- **Body** (optional): Explain what and why (separated by blank line)
- **Footer** (optional): Reference issues with `Fixes #123` or `Closes #456`

Example:
```
Add anti-smoke detection for secondary aimbot

Implements smoke filtering for secondary aimbot mode to prevent
targeting through smoke particles. Uses same detection algorithm
as main aimbot but with independent configuration.

Fixes #789
```

### Pull Request Guidelines

#### PR Title
- Use same format as commit messages
- Include issue number if applicable: `[#123] Fix config loading`

#### PR Description Template
```markdown
## What Changed
Brief description of changes.

## Why
Explanation of the problem solved or feature added.

## User-Visible Impact
- What users will notice
- Any UI/behavior changes
- Configuration changes

## Testing
- [ ] Manual testing checklist completed
- [ ] All capture backends tested (if applicable)
- [ ] Config save/load verified
- [ ] No console errors

## Screenshots/GIFs
(For UI changes, include before/after screenshots or GIFs)

## Related Issues
Closes #123
```

#### PR Requirements
- **Small and focused**: One feature or fix per PR
- **Tested**: All manual tests pass
- **Documented**: Code changes have appropriate comments/docstrings
- **Compatible**: Doesn't break existing functionality
- **Reviewed**: At least one approval before merge

#### PR Review Checklist
- Code follows style guidelines
- No hardcoded values or secrets
- Error handling is appropriate
- Configuration changes are backward compatible
- UI changes are tested on different screen sizes
- Performance impact is acceptable

## Security & Configuration Tips

### Security Best Practices
- **Never commit secrets**: API keys, tokens, passwords, or authentication credentials
- **Device identifiers are allowed**: MAC addresses (`net_uuid`, `net_mac`) and serial numbers (`serial_port`) are valid configuration options for device connection and should be included in config when needed
- **Review config changes**: Ensure `config.json` defaults are generic and safe for other contributors
- **Sanitize logs**: Don't log sensitive information (passwords, tokens, etc.)
- **Validate inputs**: Check user inputs for malicious content
- **Dependencies**: Keep dependencies up to date for security patches

### Configuration Management

#### `config.json` Guidelines
- **Default values**: Should work out-of-the-box for new users
- **Sensitive data**: Never store passwords or tokens in config
- **Device identifiers**: MAC addresses (`net_uuid`, `net_mac`) and serial numbers (`serial_port`) are valid configuration options for hardware device connection
- **Paths**: Use relative paths when possible, document absolute path requirements
- **Validation**: Validate config values on load (see `src/utils/config.py`)

#### Configuration Structure
- **Group related settings**: Use logical grouping (e.g., all aimbot settings together)
- **Naming consistency**: Use `snake_case` for all keys
- **Documentation**: Document complex parameters in code comments
- **Backward compatibility**: When changing config structure, provide migration path

#### Profile Management
- **User profiles**: Stored in `configs/*.json` (ignored by git)
- **Default template**: `configs/default.json` (tracked in repository)
- **Profile format**: Should match `config.json` structure
- **Validation**: Validate profile files before loading

### Common Configuration Patterns

#### Adding New Config Options
1. Add default value in `src/utils/config.py` `__init__` method
2. Add UI control in `src/ui.py` (if user-configurable)
3. Update `config.json` with default value
4. Document in code comments

#### Example:
```python
# In src/utils/config.py
def __init__(self):
    self.new_feature_enabled = False  # Default value
    self.new_feature_threshold = 0.5

# In src/ui.py (if needed)
self.new_feature_checkbox = ctk.CTkCheckBox(
    master=self.tab,
    text="Enable New Feature",
    variable=self.new_feature_var
)
```

## Development Workflow

### Setting Up Development Environment
1. Clone repository
2. Run `setup.bat` to create venv and install dependencies
3. Activate virtual environment: `venv\Scripts\activate`
4. Verify installation: `python main.py` (should launch UI)

### Making Changes
1. **Create feature branch**: `git checkout -b feature/your-feature-name`
2. **Make changes**: Follow coding style guidelines
3. **Test changes**: Complete manual testing checklist
4. **Commit changes**: Use proper commit message format
5. **Push and create PR**: Follow PR guidelines

### Common Development Tasks

#### Adding a New Capture Backend
1. Create new file in `src/capture/` (e.g., `new_backend.py`)
2. Implement capture interface (see `capture_service.py`)
3. Add backend option to `CaptureService`
4. Add UI controls in `src/ui.py`
5. Test connection and frame reading

#### Adding a New Aimbot Mode
1. Create new file in `src/aim_system/` (e.g., `new_mode.py`)
2. Implement mode logic (see `normal.py` for reference)
3. Add mode option to `config.py` and `ui.py`
4. Integrate with `process_normal_mode` in `normal.py`
5. Test all configuration combinations

#### Adding a New Mouse API
1. Create new file in `src/utils/mouse/` (e.g., `NewAPI.py`)
2. Implement mouse control interface (see `SerialAPI.py` for reference)
3. Add API option to `config.py` and `ui.py`
4. Update connection logic in `mouse_input.py`
5. Test connection and movement commands

### Debugging Tips

#### Common Issues
- **Import errors**: Ensure virtual environment is activated
- **Capture connection fails**: Check backend-specific requirements (NDI tools, capture card drivers)
- **Mouse API not working**: Verify device connection and port configuration
- **Config not saving**: Check file permissions and JSON syntax

#### Debug Logging
- Use `src/utils/debug_logger.py` for debug messages
- Enable OpenCV windows for visual debugging (`show_opencv_windows` in config)
- Check console output for error messages
- Use Python debugger (`pdb`) for complex issues

#### Performance Profiling
- Monitor FPS in UI (if available)
- Use `time.time()` for timing critical sections
- Profile with `cProfile`: `python -m cProfile -o profile.stats main.py`
- Analyze with `snakeviz`: `snakeviz profile.stats`

## Architecture Overview

### Application Flow
1. **Initialization** (`main.py`):
   - Create `CaptureService`
   - Initialize `AimTracker` with target FPS
   - Create `ViewerApp` (UI)
   - Load configuration

2. **Main Loop** (`AimTracker._track_loop`):
   - Runs at target FPS (default 80 FPS)
   - Each iteration calls `track_once()`

3. **Tracking Cycle** (`AimTracker.track_once`):
   - Capture frame from video source
   - Perform HSV color detection
   - Estimate target positions (head/body)
   - Process aimbot/triggerbot logic
   - Send mouse movement commands
   - Display detection windows (if enabled)

4. **Mouse Control**:
   - Movement commands queued in `move_queue`
   - Processed in separate thread (`_process_move_queue`)
   - Sent via selected mouse API (Serial, SendInput, etc.)

### Threading Model
- **Main thread**: UI (CustomTkinter event loop)
- **Tracking thread**: `AimTracker._track_loop` (runs continuously)
- **Move queue thread**: `AimTracker._process_move_queue` (processes movement commands)
- **Capture thread**: Managed by capture backend (if applicable)

### Configuration System
- **Config class** (`src/utils/config.py`): Singleton pattern, loads from `config.json`
- **Persistence**: Auto-saves on changes (via UI callbacks)
- **Validation**: Type checking and range validation on load
- **Profiles**: User profiles in `configs/*.json`, loaded on demand

## Troubleshooting

### Common Problems

#### Application Won't Start
- Check Python version: `python --version` (ensure Python 3.x is installed)
- Verify virtual environment: `venv\Scripts\python.exe --version`
- Check dependencies: `pip list` should show all required packages
- Review console errors for missing modules

#### Capture Not Working
- **NDI**: Install NDI Tools, verify source is available
- **UDP**: Check port configuration, verify stream is active
- **Capture Card**: Install device drivers, verify device is recognized
- **MSS**: Should work by default on Windows

#### Mouse API Connection Issues
- Verify device is connected and recognized by Windows
- Check port configuration (Serial port, IP address, etc.)
- Review device-specific documentation in `src/utils/mouse/API/`
- Test with device manufacturer's tools first

#### Configuration Not Saving
- Check file permissions on `config.json`
- Verify JSON syntax is valid (use JSON validator)
- Check console for error messages during save
- Ensure config directory exists and is writable

### Getting Help
- Check existing issues on GitHub
- Review code comments and docstrings
- Test with default configuration
- Enable debug logging for detailed information
- Provide error messages and system information when reporting issues
