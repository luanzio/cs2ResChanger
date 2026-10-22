"""Janela principal do CS2ResChanger.

A GUI não troca resolução de nada: ela escreve o cs2_video.txt e o
cs2-config.json. Quem aplica no desktop e o cs2-resolucao.ps1.
"""

import os
import re
import tkinter as tk

from . import daemon, vibrance
from .config_store import load_config, save_config
from .constants import APP_NAME, APP_VERSION, PRESETS, icon_path
from .cs2_file import (
    change_resolution,
    find_video_cfg,
    get_current_resolution_from_cs2,
    read_focus_loss,
    toggle_focus_loss_setting,
)
from .display_api import describe_monitors, get_current_mode, get_native_mode, list_modes
from . import theme
from .theme import P, S, F
from .widgets import (
    Button,
    Card,
    Chip,
    Input,
    Pill,
    Select,
    Slider,
    StatTile,
    Switch,
    Toast,
    card_title,
    label,
    labeled_input,
)

_MODE_RE = re.compile(r"(\d+)\s*x\s*(\d+)(?:\s*@\s*(\d+))?")

PILL_COLORS = {"ok": P.ok, "aviso": P.warn, "erro": P.danger}


def _fmt_mode(m):
    return "%dx%d @ %d Hz" % (m["width"], m["height"], m["hz"])


class App:
    def __init__(self):
        theme.enable_dpi_awareness()

        self.root = tk.Tk()
        self.root.title("%s %s" % (APP_NAME, APP_VERSION))
        self.root.configure(bg=P.bg)
        self.root.resizable(False, False)

        ico = icon_path()
        if os.path.exists(ico):
            try:
                self.root.iconbitmap(ico)
            except tk.TclError:
                pass

        theme.init(self.root)
        theme.dark_titlebar(self.root)

        self.toast = Toast(self.root)
        self.cfg = load_config()
        self._modes = []

        self._build()
        self._load_config_into_ui()
        self._refresh_display_info()
        self._refresh_focus_switch()
        self._tick_status()
        self._center()

        self.root.bind("<Return>", lambda _: self._apply())

    # ------------------------------------------------------------ layout

    def _build(self):
        wrap = tk.Frame(self.root, bg=P.bg)
        wrap.pack(fill="both", expand=True, padx=S(20), pady=S(18))

        self._build_header(wrap)
        self._build_stats(wrap)
        self._build_cards(wrap)
        self._build_vibrance(wrap)
        self._build_favorites(wrap)
        self._build_footer(wrap)

    def _build_header(self, parent):
        head = tk.Frame(parent, bg=P.bg)
        head.pack(fill="x")

        left = tk.Frame(head, bg=P.bg)
        left.pack(side="left", anchor="w")
        title = tk.Frame(left, bg=P.bg)
        title.pack(anchor="w")
        label(title, "CS2", P.bg, 19, P.accent, "bold").pack(side="left")
        label(title, "ResChanger", P.bg, 19, P.text, "bold").pack(side="left")
        label(
            left,
            "resolução do jogo e do desktop em sincronia  ·  v%s" % APP_VERSION,
            P.bg, 9.5, P.mute,
        ).pack(anchor="w", pady=(S(3), 0))

        right = tk.Frame(head, bg=P.bg)
        right.pack(side="right", anchor="e")

        self.pill = Pill(right, bg=P.bg, width=168)
        self.pill.pack(side="right")
        self.btn_log = Button(right, "Log", self._open_log, "ghost", P.bg, height=28)
        self.btn_log.pack(side="right", padx=(0, S(8)))
        self.btn_start = Button(
            right, "Iniciar daemon", self._start_daemon, "ghost", P.bg, height=28
        )

        mon = tk.Frame(head, bg=P.bg)
        mon.pack(side="right", padx=(0, S(14)))
        label(mon, "MONITOR", P.bg, 8.5, P.mute, "bold").pack(anchor="e", pady=(0, S(4)))
        self._monitors = describe_monitors()
        self.sel_monitor = Select(
            mon, bg=P.bg, values=[lbl for _v, lbl in self._monitors],
            width=228, height=28, on_change=lambda _v: self._on_monitor_change(),
        )
        self.sel_monitor.pack(anchor="e")

    def _build_stats(self, parent):
        row = tk.Frame(parent, bg=P.bg)
        row.pack(fill="x", pady=(S(16), 0))
        for i in range(3):
            row.columnconfigure(i, weight=1, uniform="stat")

        self.tile_now = StatTile(row, "Windows agora")
        self.tile_now.grid(row=0, column=0, sticky="nsew", padx=(0, S(6)))
        self.tile_native = StatTile(row, "Nativa do monitor")
        self.tile_native.grid(row=0, column=1, sticky="nsew", padx=S(6))
        self.tile_cs2 = StatTile(row, "CS2 configurado")
        self.tile_cs2.grid(row=0, column=2, sticky="nsew", padx=(S(6), 0))

    def _build_cards(self, parent):
        row = tk.Frame(parent, bg=P.bg)
        row.pack(fill="x", pady=(S(12), 0))
        row.columnconfigure(0, weight=1, uniform="card")
        row.columnconfigure(1, weight=1, uniform="card")

        # --- resolução de jogo
        game = Card(row, pad=17)
        game.grid(row=0, column=0, sticky="nsew", padx=(0, S(6)))
        b = game.body
        card_title(b, "Resolução de jogo", P.card,
                   "gravada no cs2_video.txt do CS2").pack(anchor="w")

        grid = tk.Frame(b, bg=P.card)
        grid.pack(anchor="w", pady=(S(14), 0))
        box, self.in_w = labeled_input(grid, "largura", P.card, width=148)
        box.grid(row=0, column=0, padx=(0, S(10)))
        box, self.in_h = labeled_input(grid, "altura", P.card, width=148)
        box.grid(row=0, column=1)
        box, self.in_hz = labeled_input(grid, "hz", P.card, width=148)
        box.grid(row=1, column=0, padx=(0, S(10)), pady=(S(10), 0))
        box, self.in_bpp = labeled_input(grid, "bpp", P.card, width=148, maxlen=2)
        box.grid(row=1, column=1, pady=(S(10), 0))

        label(b, "ATALHOS", P.card, 8.5, P.mute, "bold").pack(anchor="w", pady=(S(16), S(6)))
        chips = tk.Frame(b, bg=P.card)
        chips.pack(anchor="w")
        for i, preset in enumerate(PRESETS):
            Chip(
                chips, preset, P.card,
                on_click=lambda p=preset: self._apply_preset(p),
            ).grid(row=0, column=i, padx=(0, S(6)))

        label(b, "COPIAR DE", P.card, 8.5, P.mute, "bold").pack(anchor="w", pady=(S(16), S(6)))
        acts = tk.Frame(b, bg=P.card)
        acts.pack(anchor="w")
        Button(acts, "Windows atual", self._game_from_current, "ghost", P.card,
               height=30).pack(side="left", padx=(0, S(6)))
        Button(acts, "Nativa", self._game_from_native, "ghost", P.card,
               height=30).pack(side="left", padx=(0, S(6)))
        Button(acts, "cs2_video.txt", self._game_from_cs2, "ghost", P.card,
               height=30).pack(side="left")

        # --- resolução de desktop
        desk = Card(row, pad=17)
        desk.grid(row=0, column=1, sticky="nsew", padx=(S(6), 0))
        d = desk.body
        card_title(d, "Resolução do desktop", P.card,
                   "para onde o Windows volta ao fechar o CS2").pack(anchor="w")

        grid2 = tk.Frame(d, bg=P.card)
        grid2.pack(anchor="w", pady=(S(14), 0))
        box, self.in_dw = labeled_input(grid2, "largura", P.card, width=148)
        box.grid(row=0, column=0, padx=(0, S(10)))
        box, self.in_dh = labeled_input(grid2, "altura", P.card, width=148)
        box.grid(row=0, column=1)
        box, self.in_dhz = labeled_input(grid2, "hz", P.card, width=148)
        box.grid(row=1, column=0, padx=(0, S(10)), pady=(S(10), 0))

        label(d, "MODOS QUE O MONITOR ACEITA", P.card, 8.5, P.mute, "bold").pack(
            anchor="w", pady=(S(16), S(6)))
        self.sel_mode = Select(
            d, bg=P.card, values=[], width=306, height=32,
            on_change=self._desktop_from_mode, placeholder="escolher modo",
        )
        self.sel_mode.pack(anchor="w")

        label(d, "COPIAR DE", P.card, 8.5, P.mute, "bold").pack(anchor="w", pady=(S(16), S(6)))
        acts2 = tk.Frame(d, bg=P.card)
        acts2.pack(anchor="w")
        Button(acts2, "Windows atual", self._desktop_from_current, "ghost", P.card,
               height=30).pack(side="left", padx=(0, S(6)))
        Button(acts2, "Nativa", self._desktop_from_native, "ghost", P.card,
               height=30).pack(side="left")

    def _build_vibrance(self, parent):
        """Seção do digital vibrance. Só existe em máquina com NVAPI."""
        self.vib_sliders = {}
        self.vib_labels = {}
        self.sw_vibrance = None
        if not vibrance.available():
            return

        card = Card(parent, pad=14)
        card.pack(fill="x", pady=(S(12), 0))
        b = card.body

        self.sw_vibrance = Switch(
            b, "Digital vibrance", "controlado pelo daemon", P.card,
            value=bool(self.cfg.get("vibranceEnabled", False)),
            command=self._toggle_vibrance,
        )
        self.sw_vibrance.pack(side="left", padx=(0, S(22)))

        for field, titulo in (("vibranceGame", "JOGO"), ("vibranceDesktop", "DESKTOP")):
            group = tk.Frame(b, bg=P.card)
            group.pack(side="left", padx=(0, S(18)))
            label(group, titulo, P.card, 8.5, P.mute, "bold").pack(anchor="w",
                                                                   pady=(0, S(4)))
            row = tk.Frame(group, bg=P.card)
            row.pack(anchor="w")

            value = int(self.cfg.get(field, 50))
            readout = label(row, "%d%%" % value, P.card, 11, P.text, "bold",
                            width=5, anchor="w")
            slider = Slider(
                row, bg=P.card, width=132, value=value,
                on_change=lambda v, f=field: self._on_vibrance_slide(f, v),
            )
            slider.pack(side="left", padx=(0, S(8)))
            readout.pack(side="left", padx=(0, S(6)))
            Button(row, "Testar", lambda f=field: self._preview_vibrance(f),
                   "ghost", P.card, height=28).pack(side="left")

            self.vib_sliders[field] = slider
            self.vib_labels[field] = readout

        self.vib_now = label(b, "", P.card, 9.5, P.mute)
        self.vib_now.pack(side="right")
        self._sync_vibrance_enabled()

    def _build_favorites(self, parent):
        card = Card(parent, pad=17)
        card.pack(fill="x", pady=(S(12), 0))
        b = card.body

        head = tk.Frame(b, bg=P.card)
        head.pack(fill="x")
        card_title(head, "Favoritas", P.card,
                   "clique em uma para carregar nos campos de jogo").pack(side="left")
        Button(head, "+ Salvar atual", self._save_favorite, "ghost", P.card,
               height=30).pack(side="right")

        self.fav_box = tk.Frame(b, bg=P.card)
        self.fav_box.pack(fill="x", pady=(S(14), 0))

    def _build_footer(self, parent):
        card = Card(parent, pad=14)
        card.pack(fill="x", pady=(S(12), 0))
        b = card.body

        self.sw_focus = Switch(
            b, "Não minimizar no alt-tab", "lendo cs2_video.txt...", P.card,
            command=self._toggle_focus,
        )
        self.sw_focus.pack(side="left")

        self.btn_apply = Button(
            b, "APLICAR E SALVAR", self._apply, "primary", P.card,
            width=S(210), height=42, radius=11, size=11,
        )
        self.btn_apply.pack(side="right")

    def _center(self):
        self.root.update_idletasks()
        w = self.root.winfo_reqwidth()
        h = self.root.winfo_reqheight()
        x = max(0, (self.root.winfo_screenwidth() - w) // 2)
        y = max(0, (self.root.winfo_screenheight() - h) // 3)
        self.root.geometry("%dx%d+%d+%d" % (w, h, x, y))

    # ------------------------------------------------------------- estado

    def _monitor_value(self):
        chosen = self.sel_monitor.get()
        for value, lbl in self._monitors:
            if lbl == chosen:
                return value
        return "primary"

    def _load_config_into_ui(self):
        cfg = self.cfg
        cs2_w, cs2_h = get_current_resolution_from_cs2()
        self.in_w.set(cs2_w or cfg["resWidth"])
        self.in_h.set(cs2_h or cfg["resHeight"])
        self.in_hz.set(cfg["resHz"])
        self.in_bpp.set(cfg["resBPP"])
        self.in_dw.set(cfg["defaultWidth"])
        self.in_dh.set(cfg["defaultHeight"])
        self.in_dhz.set(cfg["defaultHz"])

        wanted = cfg.get("monitor", "primary")
        for value, lbl in self._monitors:
            if value == wanted:
                self.sel_monitor.set(lbl)
                break
        else:
            self.sel_monitor.set(self._monitors[0][1])

        self._rebuild_favorites()

    def _refresh_display_info(self):
        mon = self._monitor_value()
        cur = get_current_mode(mon)
        nat = get_native_mode(mon)

        if cur:
            self.tile_now.set("%dx%d" % (cur["width"], cur["height"]),
                              "%d Hz  ·  %d bpp" % (cur["hz"], cur["bpp"]))
        else:
            self.tile_now.set("N/D", "monitor não respondeu", P.warn)

        if nat:
            self.tile_native.set("%dx%d" % (nat["width"], nat["height"]),
                                 "%d Hz  ·  %d bpp" % (nat["hz"], nat["bpp"]))
        else:
            self.tile_native.set("N/D", "monitor não respondeu", P.warn)

        cs2_w, cs2_h = get_current_resolution_from_cs2()
        if cs2_w and cs2_h:
            self.tile_cs2.set("%sx%s" % (cs2_w, cs2_h), "lido do cs2_video.txt")
        elif find_video_cfg():
            self.tile_cs2.set("N/D", "sem resolução no arquivo", P.warn)
        else:
            self.tile_cs2.set("N/D", "abra o CS2 uma vez", P.warn)

        self._modes = list_modes(mon)
        self.sel_mode.set_values([_fmt_mode(m) for m in self._modes])
        self._refresh_vibrance_now()

    def _refresh_focus_switch(self):
        value, readonly = read_focus_loss()
        if value is None:
            self.sw_focus.set(False, animate=False)
            self.sw_focus.set_sub("cs2_video.txt não encontrado")
            return
        self.sw_focus.set(value == "0", animate=False)
        self.sw_focus.set_sub(
            "fullscreen_min_on_focus_loss = %s  ·  arquivo %s"
            % (value, "protegido" if readonly else "liberado")
        )

    def _tick_status(self):
        kind, text, sub = daemon.status()
        self.pill.set(text, PILL_COLORS.get(kind, P.mute))
        if daemon.can_start():
            if not self.btn_start.winfo_ismapped():
                self.btn_start.pack(side="right", padx=(0, S(8)))
        elif self.btn_start.winfo_ismapped():
            self.btn_start.pack_forget()
        self.root.after(4000, self._tick_status)

    def _rebuild_favorites(self):
        for child in self.fav_box.winfo_children():
            child.destroy()

        favs = self.cfg.get("favorites", [])
        if not favs:
            label(self.fav_box,
                  "Nenhuma favorita ainda. Ajuste os campos de jogo e clique em "
                  "“+ Salvar atual”.",
                  P.card, 10, P.mute).pack(anchor="w")
            return

        row = tk.Frame(self.fav_box, bg=P.card)
        row.pack(anchor="w")
        for i, fav in enumerate(favs):
            Chip(
                row, fav, P.card, accent=True,
                on_click=lambda f=fav: self._load_favorite(f),
                on_remove=lambda f=fav: self._remove_favorite(f),
            ).grid(row=i // 6, column=i % 6, padx=(0, S(6)), pady=(0, S(6)))

    # ------------------------------------------------------------- ações

    def _game_from_current(self):
        self._fill_game(get_current_mode(self._monitor_value()))

    def _game_from_native(self):
        self._fill_game(get_native_mode(self._monitor_value()))

    def _fill_game(self, mode):
        if not mode:
            self.toast.show("Não consegui ler o modo do monitor.", "erro")
            return
        self.in_w.set(mode["width"])
        self.in_h.set(mode["height"])
        self.in_hz.set(mode["hz"])
        self.in_bpp.set(mode["bpp"])

    def _game_from_cs2(self):
        w, h = get_current_resolution_from_cs2()
        if not (w and h):
            self.toast.show("Não consegui ler o cs2_video.txt.", "erro")
            return
        self.in_w.set(w)
        self.in_h.set(h)
        self.toast.show("Carregado do cs2_video.txt: %sx%s." % (w, h), "info")

    def _apply_preset(self, preset):
        w, h = preset.split("x")
        self.in_w.set(w)
        self.in_h.set(h)
        if not self.in_hz.get():
            cur = get_current_mode(self._monitor_value())
            if cur:
                self.in_hz.set(cur["hz"])
        if not self.in_bpp.get():
            self.in_bpp.set(32)

    def _desktop_from_current(self):
        self._fill_desktop(get_current_mode(self._monitor_value()))

    def _desktop_from_native(self):
        self._fill_desktop(get_native_mode(self._monitor_value()))

    def _fill_desktop(self, mode):
        if not mode:
            self.toast.show("Não consegui ler o modo do monitor.", "erro")
            return
        self.in_dw.set(mode["width"])
        self.in_dh.set(mode["height"])
        self.in_dhz.set(mode["hz"])

    def _desktop_from_mode(self, text):
        m = _MODE_RE.search(text or "")
        if not m:
            return
        self.in_dw.set(m.group(1))
        self.in_dh.set(m.group(2))
        if m.group(3):
            self.in_dhz.set(m.group(3))

    def _on_monitor_change(self):
        self._refresh_display_info()
        self.toast.show("Monitor: %s." % self._monitor_value(), "info", 1800)

    def _save_favorite(self):
        w, h, hz = self.in_w.get(), self.in_h.get(), self.in_hz.get()
        if not (w and h and hz):
            self.toast.show("Preencha largura, altura e Hz do jogo.", "erro")
            return
        fav = "%sx%s@%s" % (w, h, hz)
        favs = list(self.cfg.get("favorites", []))
        if fav in favs:
            self.toast.show("%s já está nas favoritas." % fav, "aviso")
            return
        favs.append(fav)
        self.cfg["favorites"] = favs
        ok, msg = save_config(self.cfg)
        if not ok:
            self.toast.show(msg, "erro")
            return
        self._rebuild_favorites()
        self.toast.show("%s salva nas favoritas." % fav, "ok")

    def _load_favorite(self, fav):
        m = _MODE_RE.search(fav)
        if not m:
            return
        self.in_w.set(m.group(1))
        self.in_h.set(m.group(2))
        if m.group(3):
            self.in_hz.set(m.group(3))
        if not self.in_bpp.get():
            self.in_bpp.set(32)
        self.toast.show("%s carregada. Clique em aplicar." % fav, "info")

    def _remove_favorite(self, fav):
        favs = [f for f in self.cfg.get("favorites", []) if f != fav]
        self.cfg["favorites"] = favs
        ok, msg = save_config(self.cfg)
        if not ok:
            self.toast.show(msg, "erro")
            return
        self._rebuild_favorites()
        self.toast.show("%s removida." % fav, "ok")

    # ---------------------------------------------------------- vibrance

    def _on_vibrance_slide(self, field, value):
        self.vib_labels[field].configure(text="%d%%" % value)

    def _toggle_vibrance(self, value):
        self.cfg["vibranceEnabled"] = bool(value)
        ok, msg = save_config(self.cfg)
        if not ok:
            self.toast.show(msg, "erro")
            return
        self._sync_vibrance_enabled()
        if value:
            self.toast.show("O daemon passa a controlar o vibrance.", "ok")
        else:
            self.toast.show("O daemon não mexe mais no vibrance.", "info")

    def _sync_vibrance_enabled(self):
        if self.sw_vibrance is None:
            return
        on = self.sw_vibrance.get()
        self.sw_vibrance.set_sub(
            "aplicado no monitor selecionado" if on else "o daemon não vai mexer"
        )
        for field, readout in self.vib_labels.items():
            readout.configure(fg=P.text if on else P.mute)

    def _preview_vibrance(self, field):
        """Aplica agora só para o usuário ver. Em jogo quem aplica é o daemon."""
        level = self.vib_sliders[field].get()
        ok, msg = vibrance.set_level(self._monitor_value(), level)
        self.toast.show(msg, "ok" if ok else "erro")
        self._refresh_vibrance_now()

    def _refresh_vibrance_now(self):
        if self.sw_vibrance is None:
            return
        level = vibrance.get_level(self._monitor_value())
        self.vib_now.configure(
            text="agora: %d%%" % level if level is not None else "agora: n/d"
        )

    def _toggle_focus(self, _value):
        ok, msg, _new = toggle_focus_loss_setting()
        self.toast.show(msg, "ok" if ok else "erro")
        self._refresh_focus_switch()

    def _open_log(self):
        ok, msg = daemon.open_log()
        if not ok:
            self.toast.show(msg, "aviso")

    def _start_daemon(self):
        ok, msg = daemon.start()
        self.toast.show(msg, "ok" if ok else "erro")

    # ------------------------------------------------------------ aplicar

    def _apply(self):
        game = [self.in_w.get(), self.in_h.get(), self.in_hz.get(), self.in_bpp.get()]
        desk = [self.in_dw.get(), self.in_dh.get(), self.in_dhz.get()]

        if not all(v.isdigit() and int(v) > 0 for v in game):
            self.toast.show("Complete largura, altura, Hz e BPP do jogo.", "erro")
            return
        if not all(v.isdigit() and int(v) > 0 for v in desk):
            self.toast.show("Complete largura, altura e Hz do desktop.", "erro")
            return

        w, h, hz, bpp = (int(v) for v in game)
        dw, dh, dhz = (int(v) for v in desk)

        ok, msg = change_resolution(str(w), str(h))
        if not ok:
            self.toast.show(msg, "erro")
            return

        self.cfg.update({
            "resWidth": w, "resHeight": h, "resHz": hz, "resBPP": bpp,
            "monitor": self._monitor_value(),
            "defaultWidth": dw, "defaultHeight": dh, "defaultHz": dhz,
        })
        if self.sw_vibrance is not None:
            self.cfg.update({
                "vibranceEnabled": self.sw_vibrance.get(),
                "vibranceGame": self.vib_sliders["vibranceGame"].get(),
                "vibranceDesktop": self.vib_sliders["vibranceDesktop"].get(),
            })
        saved, save_msg = save_config(self.cfg)
        if not saved:
            self.toast.show(save_msg, "erro")
            return

        self._refresh_display_info()
        self._refresh_focus_switch()

        # O daemon aplica a resolução de jogo no DESKTOP, entao um modo que
        # o monitor não aceita faz o nircmd falhar na hora da partida.
        warn = self._unsupported_warning(w, h, hz, dw, dh, dhz)
        if warn:
            self.toast.show(warn, "aviso", 4200)
        else:
            self.toast.show(
                "Salvo. %dx%d no jogo, %dx%d no desktop." % (w, h, dw, dh), "ok"
            )

    def _unsupported_warning(self, w, h, hz, dw, dh, dhz):
        if not self._modes:
            return None
        exact = {(m["width"], m["height"], m["hz"]) for m in self._modes}
        sizes = {(m["width"], m["height"]) for m in self._modes}
        for lbl, (a, b, c) in (("de jogo", (w, h, hz)), ("do desktop", (dw, dh, dhz))):
            if (a, b) not in sizes:
                return "Monitor não aceita %dx%d: a resolução %s pode falhar." % (a, b, lbl)
            if (a, b, c) not in exact:
                return "Monitor não lista %dx%d@%d: confira os Hz %s." % (a, b, c, lbl)
        return None

    def run(self):
        self.root.mainloop()


def create_gui():
    App().run()
