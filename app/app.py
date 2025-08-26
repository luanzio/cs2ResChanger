import os
import tkinter as tk
from tkinter import ttk, messagebox
from .constants import APP_NAME, icon_path
from .display_api import list_monitors, get_current_mode, get_native_mode
from .cs2_file import get_current_resolution_from_cs2, change_resolution, toggle_focus_loss_setting
from .config_store import load_config, save_config

def _fill_entries_from_mode(w_entry, h_entry, hz_entry, bpp_entry, mode):
    if not mode:
        messagebox.showerror("Erro", "Não foi possível obter a resolução.")
        return
    w_entry.delete(0, tk.END); w_entry.insert(0, mode["width"])
    h_entry.delete(0, tk.END); h_entry.insert(0, mode["height"])
    hz_entry.delete(0, tk.END); hz_entry.insert(0, mode["hz"])
    bpp_entry.delete(0, tk.END); bpp_entry.insert(0, mode["bpp"])

def _fill_from_cs2(w_entry, h_entry):
    w, h = get_current_resolution_from_cs2()
    if not (w and h):
        messagebox.showerror("Erro", "Não foi possível ler cs2_video.txt.")
        return
    w_entry.delete(0, tk.END); w_entry.insert(0, w)
    h_entry.delete(0, tk.END); h_entry.insert(0, h)

def _fill_defaults_from_mode(d_w_entry, d_h_entry, d_hz_entry, mode):
    if not mode:
        messagebox.showerror("Erro", "Não foi possível obter a resolução.")
        return
    d_w_entry.delete(0, tk.END); d_w_entry.insert(0, mode["width"])
    d_h_entry.delete(0, tk.END); d_h_entry.insert(0, mode["height"])
    d_hz_entry.delete(0, tk.END); d_hz_entry.insert(0, mode["hz"])

def create_gui():
    root = tk.Tk()
    root.title(f"{APP_NAME} — Configurar Resoluções")
    ico = icon_path()
    if os.path.exists(ico):
        try:
            root.iconbitmap(ico)
        except:
            pass
    style = ttk.Style()
    for t in ("vista", "xpnative", "winnative", "clam"):
        try:
            style.theme_use(t); break
        except:
            pass
    style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=8)
    style.map("Primary.TButton", relief=[("active", "raised")])
    style.configure("Danger.TButton", font=("Segoe UI", 10, "bold"), padding=8)
    style.map("Danger.TButton", relief=[("active", "raised")])
    style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"))
    style.configure("Title.TLabel", font=("Segoe UI", 12, "bold"))

    main = ttk.Frame(root, padding=10)
    main.pack(expand=True, fill="both")
    ttk.Label(main, text="CS2 — Resoluções e Perfis", style="Title.TLabel").pack(anchor="w")

    lf_monitor = ttk.LabelFrame(main, text="Monitor & Sistema", padding=10)
    lf_monitor.pack(fill="x", pady=6)
    ttk.Label(lf_monitor, text="Monitor alvo:").grid(row=0, column=0, sticky="w")
    monitor_var = tk.StringVar(value="primary")
    monitor_combo = ttk.Combobox(lf_monitor, textvariable=monitor_var, values=list_monitors(), state="readonly", width=14)
    monitor_combo.grid(row=0, column=1, padx=6, pady=3, sticky="w")
    current_var = tk.StringVar(value="—")
    native_var = tk.StringVar(value="—")
    def refresh_info():
        cm = get_current_mode(monitor_var.get())
        nm = get_native_mode(monitor_var.get())
        current_var.set(f'{cm["width"]}x{cm["height"]}@{cm["hz"]}  {cm["bpp"]}bpp' if cm else "N/D")
        native_var.set(f'{nm["width"]}x{nm["height"]}@{nm["hz"]}  {nm["bpp"]}bpp' if nm else "N/D")
    ttk.Label(lf_monitor, text="Resolução atual do Windows:").grid(row=1, column=0, sticky="w")
    ttk.Label(lf_monitor, textvariable=current_var).grid(row=1, column=1, sticky="w")
    ttk.Button(lf_monitor, text="Atualizar", command=refresh_info).grid(row=1, column=2, padx=6)
    ttk.Label(lf_monitor, text="Resolução nativa do monitor:").grid(row=2, column=0, sticky="w")
    ttk.Label(lf_monitor, textvariable=native_var).grid(row=2, column=1, sticky="w")
    ttk.Button(lf_monitor, text="Detectar", command=refresh_info).grid(row=2, column=2, padx=6)

    lf_cs2 = ttk.LabelFrame(main, text="CS2 (cs2_video.txt) — Resolução para jogar", padding=10)
    lf_cs2.pack(fill="x", pady=6)
    width_entry = ttk.Entry(lf_cs2, width=8)
    height_entry = ttk.Entry(lf_cs2, width=8)
    hz_entry = ttk.Entry(lf_cs2, width=6)
    bpp_entry = ttk.Entry(lf_cs2, width=6)
    ttk.Label(lf_cs2, text="Largura:").grid(row=0, column=0, sticky="w")
    width_entry.grid(row=0, column=1, padx=(4, 12), sticky="w")
    ttk.Label(lf_cs2, text="Altura:").grid(row=0, column=2, sticky="w")
    height_entry.grid(row=0, column=3, padx=(4, 12), sticky="w")
    ttk.Label(lf_cs2, text="Hz:").grid(row=0, column=4, sticky="w")
    hz_entry.grid(row=0, column=5, padx=(4, 12), sticky="w")
    ttk.Label(lf_cs2, text="BPP:").grid(row=0, column=6, sticky="w")
    bpp_entry.grid(row=0, column=7, padx=(4, 0), sticky="w")
    util_cs2 = ttk.Frame(lf_cs2)
    util_cs2.grid(row=1, column=0, columnspan=8, sticky="w", pady=(8, 0))
    ttk.Button(util_cs2, text="Usar resolução atual do Windows", command=lambda: _fill_entries_from_mode(width_entry, height_entry, hz_entry, bpp_entry, get_current_mode(monitor_var.get()))).pack(side="left", padx=(0, 6))
    ttk.Button(util_cs2, text="Usar resolução nativa do monitor", command=lambda: _fill_entries_from_mode(width_entry, height_entry, hz_entry, bpp_entry, get_native_mode(monitor_var.get()))).pack(side="left", padx=6)
    ttk.Button(util_cs2, text="Detectar do cs2_video.txt", command=lambda: _fill_from_cs2(width_entry, height_entry)).pack(side="left", padx=6)
    def apply_favorite_to_cs2():
        val = fav_var.get()
        if not val:
            messagebox.showerror("Erro", "Selecione uma favorita na lista primeiro.")
            return
        if "x" in val and "@" in val:
            res, hz = val.split("@")
            w, h = res.split("x")
            width_entry.delete(0, tk.END); width_entry.insert(0, w)
            height_entry.delete(0, tk.END); height_entry.insert(0, h)
            hz_entry.delete(0, tk.END); hz_entry.insert(0, hz)
            bpp_entry.delete(0, tk.END); bpp_entry.insert(0, load_config().get("resBPP", 32))
    ttk.Button(util_cs2, text="Usar favorita selecionada", command=apply_favorite_to_cs2).pack(side="left", padx=6)
    ttk.Button(lf_cs2, text="Alternar Focus Loss (cs2_video.txt)", style="Primary.TButton", command=toggle_focus_loss_setting).grid(row=2, column=0, columnspan=3, pady=(10, 0), sticky="w")

    lf_win = ttk.LabelFrame(main, text="Windows — Resolução ao sair do jogo", padding=10)
    lf_win.pack(fill="x", pady=6)
    d_w = ttk.Entry(lf_win, width=8)
    d_h = ttk.Entry(lf_win, width=8)
    d_hz = ttk.Entry(lf_win, width=6)
    ttk.Label(lf_win, text="Largura:").grid(row=0, column=0, sticky="w")
    d_w.grid(row=0, column=1, padx=(4, 12), sticky="w")
    ttk.Label(lf_win, text="Altura:").grid(row=0, column=2, sticky="w")
    d_h.grid(row=0, column=3, padx=(4, 12), sticky="w")
    ttk.Label(lf_win, text="Hz:").grid(row=0, column=4, sticky="w")
    d_hz.grid(row=0, column=5, padx=(4, 0), sticky="w")
    util_win = ttk.Frame(lf_win)
    util_win.grid(row=1, column=0, columnspan=6, sticky="w", pady=(8, 0))
    ttk.Button(util_win, text="Usar resolução atual do Windows", command=lambda: _fill_defaults_from_mode(d_w, d_h, d_hz, get_current_mode(monitor_var.get()))).pack(side="left", padx=(0, 6))
    ttk.Button(util_win, text="Usar resolução nativa do monitor", command=lambda: _fill_defaults_from_mode(d_w, d_h, d_hz, get_native_mode(monitor_var.get()))).pack(side="left", padx=6)

    actions = ttk.Frame(main)
    actions.pack(fill="x", pady=(6, 2))
    actions.columnconfigure(0, weight=1)
    actions.columnconfigure(2, weight=1)
    def on_apply():
        w = width_entry.get().strip()
        h = height_entry.get().strip()
        hz = hz_entry.get().strip()
        bpp = bpp_entry.get().strip()
        dw = d_w.get().strip()
        dh = d_h.get().strip()
        dhz = d_hz.get().strip()
        if not (w.isdigit() and h.isdigit() and hz.isdigit() and bpp.isdigit()):
            messagebox.showerror("Erro", "Valores inválidos em 'CS2 — Resolução para jogar'.")
            return
        if not (dw.isdigit() and dh.isdigit() and dhz.isdigit()):
            messagebox.showerror("Erro", "Valores inválidos em 'Windows — Resolução ao sair'.")
            return
        ok = change_resolution(w, h)
        if not ok:
            return
        cfg = load_config()
        cfg.update({"resWidth": int(w), "resHeight": int(h), "resHz": int(hz), "resBPP": int(bpp), "monitor": monitor_var.get(), "defaultWidth": int(dw), "defaultHeight": int(dh), "defaultHz": int(dhz)})
        save_config(cfg)
        messagebox.showinfo("OK", "Configurações aplicadas e salvas.")
    apply_btn = ttk.Button(actions, text="APLICAR E SALVAR", style="Primary.TButton", command=on_apply)
    apply_btn.grid(row=0, column=1, padx=6)

    cfg = load_config()
    cs2_w, cs2_h = get_current_resolution_from_cs2()
    width_entry.insert(0, cs2_w or cfg["resWidth"])
    height_entry.insert(0, cs2_h or cfg["resHeight"])
    hz_entry.insert(0, cfg["resHz"])
    bpp_entry.insert(0, cfg["resBPP"])
    d_w.insert(0, cfg["defaultWidth"])
    d_h.insert(0, cfg["defaultHeight"])
    d_hz.insert(0, cfg["defaultHz"])
    monitor_combo.set(cfg.get("monitor", "primary"))
    refresh_info()

    lf_fav = ttk.LabelFrame(main, text="Favoritas", padding=10)
    lf_fav.pack(fill="x", pady=6)
    ttk.Label(lf_fav, text="Lista (WxH@Hz):").grid(row=0, column=0, sticky="w")
    fav_var = tk.StringVar()
    fav_combo = ttk.Combobox(lf_fav, textvariable=fav_var, state="readonly", width=20)
    fav_combo.grid(row=0, column=1, padx=6, sticky="w")
    def update_fav_combo(select_last=False):
        cfg2 = load_config()
        favs = cfg2.get("favorites", [])
        fav_combo['values'] = favs
        if not favs:
            fav_var.set("")
            fav_combo.configure(state="disabled")
        else:
            fav_combo.configure(state="readonly")
            if select_last:
                fav_var.set(favs[-1])
    def save_current_as_favorite():
        w = width_entry.get().strip()
        h = height_entry.get().strip()
        hz = hz_entry.get().strip()
        if not (w.isdigit() and h.isdigit() and hz.isdigit()):
            messagebox.showerror("Erro", "Valores inválidos para salvar favorita!")
            return
        resolution = f"{w}x{h}@{hz}"
        cfg3 = load_config()
        favs = cfg3.get("favorites", [])
        if resolution not in favs:
            favs.append(resolution)
            cfg3["favorites"] = favs
            save_config(cfg3)
            update_fav_combo(select_last=True)
            messagebox.showinfo("Favorito", f"{resolution} adicionada às favoritas.")
        else:
            messagebox.showinfo("Já existe", f"{resolution} já está nas favoritas.")
    def remove_favorite():
        val = fav_var.get()
        if not val:
            messagebox.showerror("Erro", "Selecione uma favorita para remover.")
            return
        cfg4 = load_config()
        favs = cfg4.get("favorites", [])
        if val in favs:
            favs.remove(val)
            cfg4["favorites"] = favs
            save_config(cfg4)
            update_fav_combo(select_last=False)
            messagebox.showinfo("Removido", f"{val} removida.")
        else:
            messagebox.showinfo("Info", "Item não encontrado.")
    ttk.Button(lf_fav, text="Salvar atual (CS2) como favorita", style="Primary.TButton", command=save_current_as_favorite).grid(row=0, column=2, padx=6)
    ttk.Button(lf_fav, text="Remover selecionada", style="Danger.TButton", command=remove_favorite).grid(row=0, column=3, padx=6)
    update_fav_combo(False)

    root.update_idletasks()
    w_req, h_req = root.winfo_reqwidth(), root.winfo_reqheight()
    x = (root.winfo_screenwidth() - w_req) // 2
    y = (root.winfo_screenheight() - h_req) // 2
    root.geometry(f"{w_req}x{h_req}+{x}+{y}")
    root.mainloop()
