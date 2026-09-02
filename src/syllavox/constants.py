"""
Global application constants.

This module is the single source of truth for:
- application identity
- file and directory naming
- default configuration values
"""

# Application identity
#
# Syllavox is both the public product name and the runtime/storage identifier.
PRODUCT_NAME = "Syllavox"
PROJECT_VERSION = "0.7.0"
APP_NAME = PRODUCT_NAME
PACKAGE_NAME = "syllavox"

# File and directory names
SETTINGS_FILE_NAME = "settings.json"
LOGS_DIR_NAME = "logs"

# Configuration defaults
# A responsiveness-oriented default; the desktop setting can change it.
DEFAULT_MAX_TEXT_LENGTH = 1000
# Practical upper bound for one synthesis request. This is not a Piper limit;
# it prevents very large single requests while reading sessions are deferred.
MAX_CONFIGURABLE_TEXT_LENGTH = 10_000
DEFAULT_READ_HOTKEY = "Ctrl+Alt+R"
DEFAULT_TTS_BACKEND = "piper"
SHERPA_ONNX_TTS_BACKEND = "sherpa_onnx"
WINDOWS_SAPI_TTS_BACKEND = "windows_sapi"
MACOS_SYSTEM_TTS_BACKEND = "macos_system"
LINUX_ESPEAK_TTS_BACKEND = "linux_espeak_ng"
CURRENT_CONFIG_SCHEMA_VERSION = 1

# API configuration
API_HOST = "127.0.0.1"
API_PORT = 8765
API_VERSION = "v1"
API_BASE_URL = f"http://{API_HOST}:{API_PORT}/{API_VERSION}"

# Runtime asset directories
MODELS_DIR_NAME = "models"
PIPER_DIR_NAME = "piper"
SHERPA_ONNX_DIR_NAME = "sherpa-onnx"
TMP_DIR_NAME = "tmp"
RETAINED_AUDIO_DIR_NAME = "audio"
