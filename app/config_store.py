import os
import json
from .constants import CONFIG_FILE

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                pass
    return {"resWidth": 1920, "resHeight": 1080, "resHz": 60, "resBPP": 32, "monitor": "primary", "defaultWidth": 1920, "defaultHeight": 1080, "defaultHz": 60, "favorites": []}

def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
