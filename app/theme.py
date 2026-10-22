"""Paleta, fontes, escala de DPI e superficies arredondadas.

O Tk não desenha canto arredondado com antialias. Quando o Pillow está
disponível as superficies são renderizadas em 4x e reduzidas, o que da
borda lisa de verdade; sem Pillow cai no polygon suavizado do próprio
Canvas, que serve mas serrilha um pouco.
"""

import ctypes
import tkinter as tk
import tkinter.font as tkfont

try:
    from PIL import Image, ImageDraw, ImageTk
except Exception:  # pragma: no cover - fallback sem Pillow
    Image = ImageDraw = ImageTk = None


class P:
    """Paleta escura. Tons frios no fundo, ambar do CS2 no destaque."""

    bg = "#0d1014"
    card = "#151a21"
    card_hi = "#1b212a"
    field = "#1b222b"
    field_hi = "#212a35"
    border = "#242c37"
    border_hi = "#36414f"

    text = "#e7ecf3"
    dim = "#9aa6b6"
    mute = "#67727f"

    accent = "#f5a524"
    accent_hi = "#ffb545"
    accent_ink = "#1b1305"

    ok = "#3fb950"
    warn = "#d29922"
    danger = "#f85149"
    info = "#58a6ff"


_scale = 1.0
_family = "Segoe UI"
_mono = "Consolas"
_cache = {}


# ---------------------------------------------------------------- DPI


def enable_dpi_awareness():
    """Antes de criar a janela. Sem isso o Windows faz upscale borrado."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor v2
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def init(root: tk.Tk):
    """Descobre a escala real da janela e escolhe as familias de fonte."""
    global _scale, _family, _mono
    try:
        hwnd = root.winfo_id()
        dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
        if dpi:
            _scale = dpi / 96.0
    except Exception:
        _scale = 1.0

    fams = set(tkfont.families(root))
    for cand in ("Segoe UI Variable Text", "Segoe UI", "Inter", "Tahoma"):
        if cand in fams:
            _family = cand
            break
    for cand in ("Cascadia Mono", "Consolas", "Courier New"):
        if cand in fams:
            _mono = cand
            break


def S(px: float) -> int:
    """Pixels logicos -> pixels fisicos."""
    return max(1, int(round(px * _scale)))


def F(size: float, weight: str = "normal", mono: bool = False):
    """Fonte em pixels (tamanho negativo), para não brigar com `tk scaling`."""
    return (_mono if mono else _family, -S(size), weight)


# ------------------------------------------------------- titlebar escura


def dark_titlebar(root: tk.Tk):
    try:
        root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        val = ctypes.c_int(1)
        # 20 = DWMWA_USE_IMMERSIVE_DARK_MODE; 19 nas builds antigas do Win10
        for attr in (20, 19):
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attr, ctypes.byref(val), ctypes.sizeof(val)
            ) == 0:
                return
    except Exception:
        pass


# --------------------------------------------------------- superficies


def rounded(w, h, radius, fill, bg, border=None, bw=1):
    """PhotoImage de um retangulo arredondado já composto sobre `bg`.

    Retorna None se o Pillow não estiver disponível; quem chama cai no
    desenho vetorial do Canvas.
    """
    if Image is None or w <= 0 or h <= 0:
        return None
    key = (w, h, radius, fill, bg, border, bw)
    hit = _cache.get(key)
    if hit is not None:
        return hit

    ss = 4
    im = Image.new("RGB", (w * ss, h * ss), bg)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle(
        [0, 0, w * ss - 1, h * ss - 1],
        radius=max(0, radius) * ss,
        fill=fill,
        outline=border,
        width=bw * ss if border else 0,
    )
    img = ImageTk.PhotoImage(im.resize((w, h), Image.LANCZOS))
    _cache[key] = img
    return img


def round_poly(canvas: tk.Canvas, x1, y1, x2, y2, r, **kw):
    """Fallback vetorial: polygon suavizado com os cantos duplicados."""
    pts = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(pts, smooth=True, splinesteps=24, **kw)


def mix(c1: str, c2: str, t: float) -> str:
    """Interpola dois hex. Usado para estados de hover."""
    a = tuple(int(c1[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(c2[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))
