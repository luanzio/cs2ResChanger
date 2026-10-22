"""O cs2-config.json e o contrato entre a GUI e o daemon.

A GUI só escreve aqui; quem aplica resolução e o cs2-resolucao.ps1.
"""

import json
import os

from .constants import CONFIG_FILE

DEFAULTS = {
    "resWidth": 1280,
    "resHeight": 960,
    "resHz": 240,
    "resBPP": 32,
    "monitor": "primary",
    "defaultWidth": 1920,
    "defaultHeight": 1080,
    "defaultHz": 240,
    "favorites": [],
    # Digital vibrance: desligado por padrão de propósito. Ligar faz o daemon
    # assumir o controle do DVC do monitor, e quem já ajusta esse valor por
    # fora não ia querer isso acontecendo sozinho depois de uma atualização.
    "vibranceEnabled": False,
    "vibranceGame": 50,
    "vibranceDesktop": 50,
}


def load_config():
    """Sempre devolve todas as chaves: o daemon rejeita JSON incompleto."""
    cfg = dict(DEFAULTS)
    if not os.path.exists(CONFIG_FILE):
        return cfg
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return cfg
    if not isinstance(data, dict):
        return cfg

    for key, default in DEFAULTS.items():
        value = data.get(key, default)
        if key == "favorites":
            cfg[key] = [str(v) for v in value] if isinstance(value, list) else []
        elif key == "monitor":
            cfg[key] = str(value) if value else "primary"
        elif isinstance(default, bool):
            cfg[key] = bool(value)
        else:
            try:
                cfg[key] = int(value)
            except (TypeError, ValueError):
                cfg[key] = default
    return cfg


def save_config(cfg):
    """(ok, mensagem). Grava por arquivo temporario para não corromper o
    JSON se o daemon estiver lendo na mesma hora."""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        tmp = CONFIG_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        os.replace(tmp, CONFIG_FILE)
    except OSError as exc:
        return False, "Não consegui gravar %s: %s" % (CONFIG_FILE, exc)
    return True, "Configuração salva."
