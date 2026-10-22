import ctypes

ENUM_CURRENT_SETTINGS = -1
DISPLAY_DEVICE_ATTACHED = 0x1
DISPLAY_DEVICE_PRIMARY_DEVICE = 0x4

class DEVMODE(ctypes.Structure):
    _fields_ = [
        ("dmDeviceName", ctypes.c_wchar * 32),
        ("dmSpecVersion", ctypes.c_ushort),
        ("dmDriverVersion", ctypes.c_ushort),
        ("dmSize", ctypes.c_ushort),
        ("dmDriverExtra", ctypes.c_ushort),
        ("dmFields", ctypes.c_ulong),
        ("dmOrientation", ctypes.c_short),
        ("dmPaperSize", ctypes.c_short),
        ("dmPaperLength", ctypes.c_short),
        ("dmPaperWidth", ctypes.c_short),
        ("dmScale", ctypes.c_short),
        ("dmCopies", ctypes.c_short),
        ("dmDefaultSource", ctypes.c_short),
        ("dmPrintQuality", ctypes.c_short),
        ("dmColor", ctypes.c_short),
        ("dmDuplex", ctypes.c_short),
        ("dmYResolution", ctypes.c_short),
        ("dmTTOption", ctypes.c_short),
        ("dmCollate", ctypes.c_short),
        ("dmFormName", ctypes.c_wchar * 32),
        ("dmLogPixels", ctypes.c_ushort),
        ("dmBitsPerPel", ctypes.c_ulong),
        ("dmPelsWidth", ctypes.c_ulong),
        ("dmPelsHeight", ctypes.c_ulong),
        ("dmDisplayFlags", ctypes.c_ulong),
        ("dmDisplayFrequency", ctypes.c_ulong),
        ("dmICMMethod", ctypes.c_ulong),
        ("dmICMIntent", ctypes.c_ulong),
        ("dmMediaType", ctypes.c_ulong),
        ("dmDitherType", ctypes.c_ulong),
        ("dmReserved1", ctypes.c_ulong),
        ("dmReserved2", ctypes.c_ulong),
        ("dmPanningWidth", ctypes.c_ulong),
        ("dmPanningHeight", ctypes.c_ulong),
    ]

class DISPLAY_DEVICE(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("DeviceName", ctypes.c_wchar * 32),
        ("DeviceString", ctypes.c_wchar * 128),
        ("StateFlags", ctypes.c_ulong),
        ("DeviceID", ctypes.c_wchar * 128),
        ("DeviceKey", ctypes.c_wchar * 128),
    ]

EnumDisplayDevicesW = ctypes.windll.user32.EnumDisplayDevicesW
EnumDisplaySettingsW = ctypes.windll.user32.EnumDisplaySettingsW

def _get_device_name(selection: str) -> str | None:
    if selection.lower() == "primary":
        i = 0
        dd = DISPLAY_DEVICE(); dd.cb = ctypes.sizeof(DISPLAY_DEVICE)
        while EnumDisplayDevicesW(None, i, ctypes.byref(dd), 0):
            if dd.StateFlags & DISPLAY_DEVICE_PRIMARY_DEVICE:
                return dd.DeviceName
            i += 1
            dd = DISPLAY_DEVICE(); dd.cb = ctypes.sizeof(DISPLAY_DEVICE)
        return None
    if selection.isdigit():
        return f"\\\\.\\DISPLAY{selection}"
    return None

def get_current_mode(selection: str = "primary"):
    devname = _get_device_name(selection)
    dm = DEVMODE(); dm.dmSize = ctypes.sizeof(DEVMODE)
    ok = EnumDisplaySettingsW(devname, ENUM_CURRENT_SETTINGS, ctypes.byref(dm))
    if not ok:
        return None
    return {"width": int(dm.dmPelsWidth), "height": int(dm.dmPelsHeight), "hz": int(dm.dmDisplayFrequency), "bpp": int(dm.dmBitsPerPel)}

def get_native_mode(selection: str = "primary"):
    devname = _get_device_name(selection)
    i = 0; best = None
    while True:
        dm = DEVMODE(); dm.dmSize = ctypes.sizeof(DEVMODE)
        ok = EnumDisplaySettingsW(devname, i, ctypes.byref(dm))
        if not ok: break
        area = int(dm.dmPelsWidth) * int(dm.dmPelsHeight)
        hz = int(dm.dmDisplayFrequency) or 60
        cand = {"width": int(dm.dmPelsWidth), "height": int(dm.dmPelsHeight), "hz": hz, "bpp": int(dm.dmBitsPerPel), "area": area}
        if (best is None) or (cand["area"] > best["area"]) or (cand["area"] == best["area"] and cand["hz"] > best["hz"]):
            best = cand
        i += 1
    if best:
        return {k: best[k] for k in ("width", "height", "hz", "bpp")}
    return None

def list_modes(selection: str = "primary"):
    """Todos os modos que o driver aceita nesse monitor, sem repetir.

    Ordenado do maior para o menor, Hz decrescente. O daemon aplica a
    resolução do jogo no desktop, então só faz sentido oferecer modos
    que o monitor realmente suporta.
    """
    devname = _get_device_name(selection)
    seen = {}
    i = 0
    while True:
        dm = DEVMODE(); dm.dmSize = ctypes.sizeof(DEVMODE)
        if not EnumDisplaySettingsW(devname, i, ctypes.byref(dm)):
            break
        i += 1
        if int(dm.dmBitsPerPel) < 32:
            continue
        key = (int(dm.dmPelsWidth), int(dm.dmPelsHeight), int(dm.dmDisplayFrequency))
        seen[key] = {"width": key[0], "height": key[1], "hz": key[2],
                     "bpp": int(dm.dmBitsPerPel)}
    return [seen[k] for k in sorted(seen, key=lambda k: (-k[0] * k[1], -k[2]))]


def _enum_devices():
    i = 0
    out = []
    dd = DISPLAY_DEVICE(); dd.cb = ctypes.sizeof(DISPLAY_DEVICE)
    while EnumDisplayDevicesW(None, i, ctypes.byref(dd), 0):
        out.append((dd.DeviceName, dd.DeviceString, int(dd.StateFlags)))
        i += 1
        dd = DISPLAY_DEVICE(); dd.cb = ctypes.sizeof(DISPLAY_DEVICE)
    return out


def list_monitors():
    idxs = []
    for name, _desc, flags in _enum_devices():
        if not (flags & DISPLAY_DEVICE_ATTACHED):
            continue
        if name.startswith("\\\\.\\DISPLAY"):
            try:
                idxs.append(int(name.replace("\\\\.\\DISPLAY", "")))
            except ValueError:
                pass
    return ["primary"] + [str(n) for n in sorted(set(idxs))]


def _monitor_name(adapter: str) -> str:
    """Nome da tela ligada no adaptador.

    A enumeração de primeiro nível devolve a placa de vídeo, então dois
    monitores na mesma GPU apareceriam com o mesmo rótulo. O nome da tela
    está no segundo nível.
    """
    dd = DISPLAY_DEVICE(); dd.cb = ctypes.sizeof(DISPLAY_DEVICE)
    if EnumDisplayDevicesW(adapter, 0, ctypes.byref(dd), 0):
        return dd.DeviceString or ""
    return ""


def describe_monitors():
    """[(valor_do_config, rótulo_para_a_UI)] só com monitores ligados."""
    out = [("primary", "primary — monitor principal")]
    for name, desc, flags in _enum_devices():
        if not (flags & DISPLAY_DEVICE_ATTACHED):
            continue
        if not name.startswith("\\\\.\\DISPLAY"):
            continue
        num = name.replace("\\\\.\\DISPLAY", "")
        if not num.isdigit():
            continue
        title = _monitor_name(name) or desc or "monitor"
        mode = get_current_mode(num)
        extra = " · %dx%d" % (mode["width"], mode["height"]) if mode else ""
        tag = " (principal)" if flags & DISPLAY_DEVICE_PRIMARY_DEVICE else ""
        out.append((num, "%s — %s%s%s" % (num, title, extra, tag)))
    return out
