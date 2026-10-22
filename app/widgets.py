"""Widgets desenhados a mao.

O ttk no Windows não aceita tema escuro de verdade: botão, entry e
combobox vem do visual style nativo e ignoram cor de fundo. Entao o
conjunto abaixo e desenhado em Canvas, o que da controle total de cor,
raio e estado de hover sem dependencia de UI externa.
"""

import tkinter as tk
import tkinter.font as tkfont

from . import theme
from .theme import P, S, F


def label(parent, text, bg, size=11, color=P.text, weight="normal", **kw):
    return tk.Label(parent, text=text, bg=bg, fg=color, font=F(size, weight), **kw)


class _Round(tk.Canvas):
    """Canvas de tamanho fixo com uma superficie arredondada ao fundo."""

    def __init__(self, parent, w, h, bg):
        super().__init__(
            parent, width=w, height=h, bg=bg,
            highlightthickness=0, bd=0, takefocus=0,
        )
        self.cw, self.ch, self.cbg = w, h, bg
        self._keep = {}

    def paint(self, radius, fill, border=None, bw=1):
        self.delete("shape")
        img = theme.rounded(self.cw, self.ch, radius, fill, self.cbg, border, bw)
        if img is not None:
            self._keep["shape"] = img
            self.create_image(0, 0, image=img, anchor="nw", tags="shape")
        else:
            theme.round_poly(
                self, bw, bw, self.cw - bw - 1, self.ch - bw - 1, radius,
                fill=fill, outline=border or fill, width=bw, tags="shape",
            )
        self.tag_lower("shape")


# ------------------------------------------------------------------ Card


class Card(tk.Frame):
    """Painel arredondado. O conteudo vai em `.body`.

    O fundo e um Canvas posicionado com place() atras do corpo, entao o
    tamanho pedido continua vindo do conteudo e não precisa ser fixado.
    """

    def __init__(self, parent, bg=P.bg, fill=P.card, radius=14, pad=16,
                 border=P.border):
        super().__init__(parent, bg=bg)
        self._fill, self._radius, self._border, self.cbg = fill, radius, border, bg
        self._canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0, takefocus=0)
        self._canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.body = tk.Frame(self, bg=fill)
        self.body.pack(fill="both", expand=True, padx=S(pad), pady=S(pad))
        self._keep = None
        self._size = (0, 0)
        self.bind("<Configure>", self._repaint)

    def _repaint(self, ev):
        if (ev.width, ev.height) == self._size or ev.width < 4:
            return
        self._size = (ev.width, ev.height)
        self._canvas.delete("all")
        img = theme.rounded(
            ev.width, ev.height, S(self._radius), self._fill, self.cbg,
            self._border, 1,
        )
        if img is not None:
            self._keep = img
            self._canvas.create_image(0, 0, image=img, anchor="nw")
        else:
            theme.round_poly(
                self._canvas, 0, 0, ev.width - 1, ev.height - 1, S(self._radius),
                fill=self._fill, outline=self._border or self._fill, width=1,
            )


def card_title(parent, text, bg, sub=None):
    """Titulo de seção: barrinha ambar + texto, opcionalmente com legenda."""
    head = tk.Frame(parent, bg=bg)
    row = tk.Frame(head, bg=bg)
    row.pack(anchor="w")
    bar = tk.Frame(row, bg=P.accent, width=S(3), height=S(13))
    bar.pack(side="left", padx=(0, S(8)))
    bar.pack_propagate(False)
    label(row, text, bg, 11, P.text, "bold").pack(side="left")
    if sub:
        label(head, sub, bg, 9.5, P.mute).pack(anchor="w", pady=(S(3), 0))
    return head


# ---------------------------------------------------------------- Button


class Button(_Round):
    KINDS = {
        "primary": dict(fill=P.accent, hover=P.accent_hi, fg=P.accent_ink,
                        border=None, weight="bold"),
        "ghost": dict(fill=P.field, hover=P.field_hi, fg=P.dim,
                      border=P.border, weight="normal"),
        "danger": dict(fill=P.field, hover="#2b1c1e", fg=P.danger,
                       border="#3a2529", weight="normal"),
    }

    def __init__(self, parent, text, command=None, kind="ghost", bg=P.card,
                 width=None, height=34, radius=9, size=10.5, padx=14):
        self.k = dict(self.KINDS[kind])
        self._font = F(size, self.k["weight"])
        self._text = text
        self._command = command
        self._enabled = True
        self._hover = False

        fm = tkfont.Font(root=parent, font=self._font)
        w = width if width is not None else (fm.measure(text) + 2 * S(padx))
        super().__init__(parent, int(w), S(height), bg)
        self._radius = S(radius)

        self._label = self.create_text(
            self.cw // 2, self.ch // 2 + 1, text=text,
            fill=self.k["fg"], font=self._font,
        )
        self._render()

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.configure(cursor="hand2")

    # --- estado

    def _render(self, pressed=False):
        if not self._enabled:
            fill, fg = P.field, P.mute
        elif pressed:
            fill = theme.mix(self.k["fill"], "#000000", 0.18)
            fg = self.k["fg"]
        else:
            fill = self.k["hover"] if self._hover else self.k["fill"]
            fg = self.k["fg"]
        self.paint(self._radius, fill, self.k["border"], 1)
        self.itemconfigure(self._label, fill=fg, text=self._text)

    def set_text(self, text):
        self._text = text
        self._render()

    def set_enabled(self, on):
        self._enabled = bool(on)
        self.configure(cursor="hand2" if on else "arrow")
        self._render()

    # --- eventos

    def _on_enter(self, _):
        self._hover = True
        self._render()

    def _on_leave(self, _):
        self._hover = False
        self._render()

    def _on_press(self, _):
        if self._enabled:
            self._render(pressed=True)

    def _on_release(self, ev):
        if not self._enabled:
            return
        self._render()
        inside = 0 <= ev.x <= self.cw and 0 <= ev.y <= self.ch
        if inside and self._command:
            self._command()


# ----------------------------------------------------------------- Input


class Input(_Round):
    """Campo de texto arredondado com anel de foco ambar."""

    def __init__(self, parent, bg=P.card, width=110, height=34, radius=9,
                 digits=True, maxlen=5, align="center", on_change=None):
        super().__init__(parent, S(width), S(height), bg)
        self._radius = S(radius)
        self._focused = False
        self.var = tk.StringVar()
        if on_change:
            self.var.trace_add("write", lambda *_: on_change())

        self.entry = tk.Entry(
            self, textvariable=self.var, bd=0, highlightthickness=0,
            bg=P.field, fg=P.text, insertbackground=P.accent,
            font=F(12), justify=align, disabledbackground=P.field,
        )
        if digits:
            vc = self.register(lambda s: s == "" or (s.isdigit() and len(s) <= maxlen))
            self.entry.configure(validate="key", validatecommand=(vc, "%P"))

        pad = S(10)
        self.create_window(
            pad, self.ch // 2, window=self.entry, anchor="w",
            width=self.cw - 2 * pad, height=self.ch - S(12),
        )
        self.entry.bind("<FocusIn>", self._focus_in)
        self.entry.bind("<FocusOut>", self._focus_out)
        self.bind("<Button-1>", lambda _: self.entry.focus_set())
        self._render()

    def _render(self):
        border = P.accent if self._focused else P.border
        self.paint(self._radius, P.field, border, 1)

    def _focus_in(self, _):
        self._focused = True
        self._render()

    def _focus_out(self, _):
        self._focused = False
        self._render()

    def get(self):
        return self.var.get().strip()

    def set(self, value):
        self.var.set("" if value is None else str(value))


def labeled_input(parent, text, bg, **kw):
    """Rótulo pequeno acima do campo. Devolve (frame, Input)."""
    box = tk.Frame(parent, bg=bg)
    label(box, text.upper(), bg, 8.5, P.mute, "bold").pack(anchor="w", pady=(0, S(4)))
    inp = Input(box, bg=bg, **kw)
    inp.pack(anchor="w")
    return box, inp


# ---------------------------------------------------------------- Select


class Select(_Round):
    """Dropdown próprio: gatilho em Canvas + popup com lista escura."""

    def __init__(self, parent, bg=P.card, values=(), value=None, width=170,
                 height=34, radius=9, on_change=None, placeholder="selecionar"):
        super().__init__(parent, S(width), S(height), bg)
        self._radius = S(radius)
        self._values = list(values)
        self._value = value
        self._placeholder = placeholder
        self._on_change = on_change
        self._hover = False
        self._popup = None

        self._text_id = self.create_text(
            S(12), self.ch // 2 + 1, anchor="w", font=F(11), fill=P.text,
        )
        self._arrow = self.create_text(
            self.cw - S(13), self.ch // 2, anchor="e", text="▾",
            font=F(10), fill=P.mute,
        )
        self._render()

        self.bind("<Enter>", lambda _: self._set_hover(True))
        self.bind("<Leave>", lambda _: self._set_hover(False))
        self.bind("<Button-1>", lambda _: self.toggle())
        self.configure(cursor="hand2")

    # --- aparência

    def _render(self):
        open_ = self._popup is not None
        border = P.accent if open_ else (P.border_hi if self._hover else P.border)
        self.paint(self._radius, P.field_hi if self._hover else P.field, border, 1)
        shown = self._value if self._value else self._placeholder
        self.itemconfigure(
            self._text_id, text=self._ellipsis(str(shown)),
            fill=P.text if self._value else P.mute,
        )

    def _ellipsis(self, s):
        fm = tkfont.Font(root=self, font=F(11))
        room = self.cw - S(34)
        if fm.measure(s) <= room:
            return s
        while s and fm.measure(s + "…") > room:
            s = s[:-1]
        return s + "…"

    def _set_hover(self, on):
        self._hover = on
        self._render()

    # --- dados

    def set_values(self, values, keep=True):
        self._values = list(values)
        if not keep or self._value not in self._values:
            self._value = None
        self._render()

    def get(self):
        return self._value

    def set(self, value, notify=False):
        self._value = value
        self._render()
        if notify and self._on_change:
            self._on_change(value)

    # --- popup

    def toggle(self):
        if self._popup is not None:
            self._close()
        else:
            self._open()

    def _open(self):
        if not self._values:
            return
        top = tk.Toplevel(self)
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        top.configure(bg=P.border_hi)

        rows = min(len(self._values), 11)
        lb = tk.Listbox(
            top, bd=0, highlightthickness=0, relief="flat", activestyle="none",
            bg=P.card_hi, fg=P.text, selectbackground=P.accent,
            selectforeground=P.accent_ink, font=F(11), height=rows,
            exportselection=False,
        )
        lb.pack(fill="both", expand=True, padx=1, pady=1)
        for v in self._values:
            lb.insert("end", "  %s" % v)
        if self._value in self._values:
            i = self._values.index(self._value)
            lb.selection_set(i)
            lb.see(i)

        self.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.ch + S(4)
        top.geometry("%dx%d+%d+%d" % (self.cw, lb.winfo_reqheight() + 2, x, y))

        self._popup = top
        self._render()

        lb.bind("<ButtonRelease-1>", lambda _: self._pick(lb))
        lb.bind("<Return>", lambda _: self._pick(lb))
        lb.bind("<Escape>", lambda _: self._close())
        top.bind("<Escape>", lambda _: self._close())
        top.bind("<FocusOut>", lambda _: self._close())
        top.bind("<Button-1>", self._maybe_outside)
        top.grab_set()
        lb.focus_set()

    def _maybe_outside(self, ev):
        top = self._popup
        if top is None:
            return
        inside = (
            top.winfo_rootx() <= ev.x_root <= top.winfo_rootx() + top.winfo_width()
            and top.winfo_rooty() <= ev.y_root <= top.winfo_rooty() + top.winfo_height()
        )
        if not inside:
            self._close()

    def _pick(self, lb):
        sel = lb.curselection()
        if sel:
            self._value = self._values[sel[0]]
        self._close()
        if sel and self._on_change:
            self._on_change(self._value)

    def _close(self):
        top, self._popup = self._popup, None
        if top is not None:
            try:
                top.grab_release()
                top.destroy()
            except Exception:
                pass
        self._render()


# ------------------------------------------------------------------ Chip


class Chip(_Round):
    """Pílula clicavel. Com `on_remove` ganha um x no canto direito."""

    def __init__(self, parent, text, bg=P.card, on_click=None, on_remove=None,
                 height=28, radius=14, size=10, accent=False):
        self._font = F(size, "bold" if accent else "normal")
        fm = tkfont.Font(root=parent, font=self._font)
        padx = S(12)
        w = fm.measure(text) + 2 * padx + (S(16) if on_remove else 0)
        super().__init__(parent, int(w), S(height), bg)

        self._radius = S(radius)
        self._accent = accent
        self._hover = False
        self._on_click = on_click
        self._on_remove = on_remove

        self._label = self.create_text(
            padx, self.ch // 2 + 1, anchor="w", text=text, font=self._font,
        )
        self._x_id = None
        if on_remove:
            self._x_id = self.create_text(
                self.cw - S(11), self.ch // 2, anchor="center", text="×",
                font=F(12), fill=P.mute,
            )
            self.tag_bind(self._x_id, "<Enter>",
                          lambda _: self.itemconfigure(self._x_id, fill=P.danger))
            self.tag_bind(self._x_id, "<Leave>",
                          lambda _: self.itemconfigure(self._x_id, fill=P.mute))
            self.tag_bind(self._x_id, "<Button-1>", self._remove)

        self._render()
        self.bind("<Enter>", lambda _: self._set_hover(True))
        self.bind("<Leave>", lambda _: self._set_hover(False))
        self.bind("<Button-1>", self._click)
        self.configure(cursor="hand2")

    def _render(self):
        if self._accent:
            fill = theme.mix(P.accent, P.card, 0.80 if not self._hover else 0.70)
            fg, border = P.accent_hi, theme.mix(P.accent, P.card, 0.55)
        else:
            fill = P.field_hi if self._hover else P.field
            fg, border = P.dim, P.border
        self.paint(self._radius, fill, border, 1)
        self.itemconfigure(self._label, fill=fg)

    def _set_hover(self, on):
        self._hover = on
        self._render()

    def _click(self, ev):
        # clique no x e tratado pelo tag_bind, que roda antes
        if self._x_id is not None and ev.x > self.cw - S(22):
            return
        if self._on_click:
            self._on_click()

    def _remove(self, _):
        if self._on_remove:
            self._on_remove()
        return "break"


# ---------------------------------------------------------------- Switch


class Switch(tk.Frame):
    """Chave animada com titulo e legenda."""

    def __init__(self, parent, text, sub=None, bg=P.card, value=False,
                 command=None, width=46, height=24):
        super().__init__(parent, bg=bg)
        self._value = bool(value)
        self._command = command
        self.cw, self.ch = S(width), S(height)
        self._anim = None

        self.track = tk.Canvas(
            self, width=self.cw, height=self.ch, bg=bg,
            highlightthickness=0, bd=0, takefocus=0, cursor="hand2",
        )
        self.track.pack(side="left", padx=(0, S(10)))
        self._keep = {}

        texts = tk.Frame(self, bg=bg)
        texts.pack(side="left", fill="y")
        self._title = label(texts, text, bg, 11, P.text, "bold")
        self._title.pack(anchor="w")
        self._sub = None
        if sub is not None:
            self._sub = label(texts, sub, bg, 9.5, P.mute)
            self._sub.pack(anchor="w", pady=(S(2), 0))

        self._knob_x = self._off_x() if not self._value else self._on_x()
        self._draw()
        for w in (self.track, self._title, texts, self):
            w.bind("<Button-1>", self._toggle)
        if self._sub is not None:
            self._sub.bind("<Button-1>", self._toggle)

    # --- geometria do knob

    def _pad(self):
        return S(3)

    def _d(self):
        return self.ch - 2 * self._pad()

    def _off_x(self):
        return self._pad()

    def _on_x(self):
        return self.cw - self._pad() - self._d()

    def _draw(self):
        self.track.delete("all")
        fill = P.ok if self._value else P.field
        border = theme.mix(P.ok, "#000000", 0.35) if self._value else P.border_hi
        img = theme.rounded(self.cw, self.ch, self.ch // 2, fill,
                            self.track["bg"], border, 1)
        if img is not None:
            self._keep["t"] = img
            self.track.create_image(0, 0, image=img, anchor="nw")
        else:
            theme.round_poly(self.track, 0, 0, self.cw - 1, self.ch - 1,
                             self.ch // 2, fill=fill, outline=border, width=1)
        d = self._d()
        y = self._pad()
        self.track.create_oval(
            self._knob_x, y, self._knob_x + d, y + d,
            fill="#f2f5f9" if self._value else "#8e9aa8", outline="",
        )

    # --- estado

    def get(self):
        return self._value

    def set(self, value, animate=True, notify=False):
        value = bool(value)
        changed = value != self._value
        self._value = value
        if animate and changed:
            self._animate()
        else:
            self._knob_x = self._on_x() if value else self._off_x()
            self._draw()
        if notify and changed and self._command:
            self._command(self._value)

    def set_sub(self, text):
        if self._sub is not None:
            self._sub.configure(text=text)

    def _animate(self, step=0, steps=7):
        start = self._off_x() if self._value else self._on_x()
        end = self._on_x() if self._value else self._off_x()
        t = (step + 1) / steps
        t = 1 - (1 - t) ** 3  # ease-out
        self._knob_x = int(round(start + (end - start) * t))
        self._draw()
        if step + 1 < steps:
            self._anim = self.after(12, self._animate, step + 1, steps)

    def _toggle(self, _=None):
        self.set(not self._value, notify=True)


# ---------------------------------------------------------------- Slider


class Slider(tk.Canvas):
    """Controle deslizante. Arrastar ou clicar em qualquer ponto da trilha."""

    def __init__(self, parent, bg=P.card, width=150, height=26,
                 minimum=0, maximum=100, value=50, on_change=None):
        self.cw, self.ch = S(width), S(height)
        super().__init__(parent, width=self.cw, height=self.ch, bg=bg,
                         highlightthickness=0, bd=0, takefocus=0, cursor="hand2")
        self._min, self._max = minimum, maximum
        self._value = value
        self._on_change = on_change
        self._hover = False
        self._r = max(S(6), self.ch // 2 - S(4))

        self.bind("<Button-1>", self._jump)
        self.bind("<B1-Motion>", self._jump)
        self.bind("<Enter>", lambda _: self._set_hover(True))
        self.bind("<Leave>", lambda _: self._set_hover(False))
        self._draw()

    # --- geometria

    def _x0(self):
        return self._r + S(1)

    def _x1(self):
        return self.cw - self._r - S(1)

    def _knob_x(self):
        span = max(1, self._max - self._min)
        t = (self._value - self._min) / span
        return self._x0() + t * (self._x1() - self._x0())

    def _draw(self):
        self.delete("all")
        cy = self.ch // 2
        kx = self._knob_x()
        self.create_line(self._x0(), cy, self._x1(), cy, width=S(4),
                         fill=P.border_hi, capstyle="round")
        if kx > self._x0():
            self.create_line(self._x0(), cy, kx, cy, width=S(4),
                             fill=P.accent, capstyle="round")
        r = self._r + (S(1) if self._hover else 0)
        self.create_oval(kx - r, cy - r, kx + r, cy + r,
                         fill="#f4f7fb" if self._hover else "#e2e8f0", outline="")

    def _set_hover(self, on):
        self._hover = on
        self._draw()

    # --- estado

    def get(self):
        return self._value

    def set(self, value, notify=False):
        value = max(self._min, min(self._max, int(value)))
        changed = value != self._value
        self._value = value
        self._draw()
        if notify and changed and self._on_change:
            self._on_change(value)

    def _jump(self, ev):
        span = self._x1() - self._x0()
        if span <= 0:
            return
        t = (ev.x - self._x0()) / span
        t = max(0.0, min(1.0, t))
        self.set(round(self._min + t * (self._max - self._min)), notify=True)


# -------------------------------------------------------------- StatTile


class StatTile(Card):
    """Cartao pequeno de leitura: rótulo, valor grande e legenda."""

    def __init__(self, parent, title, bg=P.bg):
        super().__init__(parent, bg=bg, fill=P.card, radius=12, pad=13)
        label(self.body, title.upper(), P.card, 8.5, P.mute, "bold").pack(anchor="w")
        self._value = label(self.body, "—", P.card, 17, P.text, "bold")
        self._value.pack(anchor="w", pady=(S(5), 0))
        self._sub = label(self.body, " ", P.card, 9.5, P.dim)
        self._sub.pack(anchor="w", pady=(S(2), 0))

    def set(self, value, sub=" ", color=P.text):
        self._value.configure(text=value, fg=color)
        self._sub.configure(text=sub)


# ------------------------------------------------------------------ Pill


class Pill(_Round):
    """Indicador de status: bolinha colorida + texto."""

    def __init__(self, parent, bg=P.bg, width=150, height=28, radius=14):
        super().__init__(parent, S(width), S(height), bg)
        self._radius = S(radius)
        d = S(7)
        cy = self.ch // 2
        self._dot = self.create_oval(S(12), cy - d // 2, S(12) + d, cy + d // 2,
                                     fill=P.mute, outline="")
        self._text = self.create_text(S(12) + d + S(8), cy + 1, anchor="w",
                                      text="", font=F(10), fill=P.dim)
        self.paint(self._radius, P.card, P.border, 1)

    def set(self, text, color=P.mute):
        self.itemconfigure(self._dot, fill=color)
        self.itemconfigure(self._text, text=text, fill=P.dim)


# ----------------------------------------------------------------- Toast


class Toast:
    """Aviso flutuante no rodape. Substitui as messagebox do Windows."""

    COLORS = {"ok": P.ok, "erro": P.danger, "info": P.info, "aviso": P.warn}

    def __init__(self, root):
        self.root = root
        self._canvas = None
        self._job = None

    def show(self, message, kind="ok", ms=2800):
        self.hide()
        font = F(10.5)
        fm = tkfont.Font(root=self.root, font=font)
        pad = S(16)
        w = fm.measure(message) + 2 * pad + S(18)
        h = S(38)

        c = _Round(self.root, int(w), h, P.bg)
        c.paint(h // 2, P.card_hi, P.border_hi, 1)
        d = S(8)
        c.create_oval(pad, h // 2 - d // 2, pad + d, h // 2 + d // 2,
                      fill=self.COLORS.get(kind, P.info), outline="")
        c.create_text(pad + d + S(10), h // 2 + 1, anchor="w", text=message,
                      font=font, fill=P.text)
        c.place(relx=0.5, rely=1.0, anchor="s", y=-S(18))
        c.lift()

        self._canvas = c
        self._job = self.root.after(ms, self.hide)

    def hide(self):
        if self._job is not None:
            try:
                self.root.after_cancel(self._job)
            except Exception:
                pass
            self._job = None
        if self._canvas is not None:
            try:
                self._canvas.destroy()
            except Exception:
                pass
            self._canvas = None
