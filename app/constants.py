import os
import sys

APP_NAME = "CS2ResTool"
CONFIG_FILE = r"C:\nircmd\cs2-config.json"

def icon_path():
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, "assets", "cs2.ico")
