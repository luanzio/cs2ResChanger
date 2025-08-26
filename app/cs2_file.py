import os
import re
from tkinter import messagebox

def find_video_cfg():
    steam_path = r"C:\\Program Files (x86)\\Steam\\userdata"
    if not os.path.exists(steam_path):
        return None
    for user_id in os.listdir(steam_path):
        cfg_path = os.path.join(steam_path, user_id, "730", "local", "cfg", "cs2_video.txt")
        if os.path.exists(cfg_path):
            return cfg_path
    return None

def _read_file_text(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def _write_file_text(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def _get_focus_loss_value(content: str) -> str | None:
    m = re.search(r'"setting\.fullscreen_min_on_focus_loss"\s+"(\d+)"', content)
    return m.group(1) if m else None

def get_current_resolution_from_cs2():
    file_path = find_video_cfg()
    if not file_path:
        return None, None
    content = _read_file_text(file_path)
    width_match = re.search(r'"setting\.defaultres"\s+"(\d+)"', content)
    height_match = re.search(r'"setting\.defaultresheight"\s+"(\d+)"', content)
    if width_match and height_match:
        return width_match.group(1), height_match.group(1)
    return None, None

def change_resolution(new_width, new_height):
    file_path = find_video_cfg()
    if not file_path:
        messagebox.showerror("Erro", "cs2_video.txt não encontrado. Abra o CS2 ao menos uma vez.")
        return False
    try:
        os.chmod(file_path, 0o666)
    except:
        pass
    content = _read_file_text(file_path)
    focus_val = _get_focus_loss_value(content)
    if focus_val not in ("0", "1"):
        focus_val = "0"
    content = re.sub(r'("setting\.defaultres"\s+"\d+")', f'"setting.defaultres" "{new_width}"', content)
    content = re.sub(r'("setting\.defaultresheight"\s+"\d+")', f'"setting.defaultresheight" "{new_height}"', content)
    _write_file_text(file_path, content)
    try:
        os.chmod(file_path, 0o444 if focus_val == "0" else 0o666)
    except:
        pass
    messagebox.showinfo("Sucesso", f"Resolução do CS2 alterada para {new_width}x{new_height}.")
    return True

def toggle_focus_loss_setting():
    file_path = find_video_cfg()
    if not file_path:
        messagebox.showerror("Erro", "cs2_video.txt não encontrado. Abra o CS2 ao menos uma vez.")
        return
    try:
        os.chmod(file_path, 0o666)
    except:
        pass
    content = _read_file_text(file_path)
    match = re.search(r'"setting\.fullscreen_min_on_focus_loss"\s+"(\d+)"', content)
    if not match:
        insert_after = re.search(r'("setting\.defaultresheight"\s+"\d+")', content)
        to_add = '\n\t\t"setting.fullscreen_min_on_focus_loss"\t\t"0"'
        if insert_after:
            content = content.replace(insert_after.group(1), insert_after.group(1) + to_add)
        else:
            content = content.strip() + to_add + "\n"
        new_val = "0"
    else:
        current_val = match.group(1)
        new_val = "1" if current_val == "0" else "0"
        content = re.sub(r'("setting\.fullscreen_min_on_focus_loss"\s+"\d+")', f'"setting.fullscreen_min_on_focus_loss" "{new_val}"', content)
    _write_file_text(file_path, content)
    try:
        os.chmod(file_path, 0o444 if new_val == "0" else 0o666)
    except:
        pass
    if new_val == "0":
        messagebox.showinfo("Focus Loss", "Focus loss = 0. Arquivo protegido (somente leitura).")
    else:
        messagebox.showinfo("Focus Loss", "Focus loss = 1. Arquivo liberado para edição.")
