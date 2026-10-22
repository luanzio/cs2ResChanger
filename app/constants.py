import os
import sys

APP_NAME = "CS2ResChanger"
APP_VERSION = "2.0.0"

NIRCMD_DIR = r"C:\nircmd"
NIRCMD_EXE = os.path.join(NIRCMD_DIR, "nircmd.exe")
CONFIG_FILE = os.path.join(NIRCMD_DIR, "cs2-config.json")
LOG_FILE = os.path.join(NIRCMD_DIR, "cs2-resolucao.log")
DAEMON_PS1 = os.path.join(NIRCMD_DIR, "cs2-resolucao.ps1")
DAEMON_VBS = os.path.join(NIRCMD_DIR, "cs2-resolucao.vbs")

# Tem que casar com $MutexName no cs2-resolucao.ps1.
DAEMON_MUTEX = r"Local\cs2-resolucao-v2"

# Resolucoes que a cena de CS usa mais; viram atalhos na GUI.
PRESETS = ["1280x960", "1024x768", "1440x1080", "1920x1080"]


def icon_path():
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, "assets", "cs2.ico")
