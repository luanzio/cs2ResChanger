import ctypes

ENUM_CURRENT_SETTINGS = -1
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

def list_monitors():
    out = []; idxs = []; i = 0
    dd = DISPLAY_DEVICE(); dd.cb = ctypes.sizeof(DISPLAY_DEVICE)
    while EnumDisplayDevicesW(None, i, ctypes.byref(dd), 0):
        name = dd.DeviceName
        if name.startswith("\\\\.\\DISPLAY"):
            try: idxs.append(int(name.replace("\\\\.\\DISPLAY", "")))
            except: pass
        i += 1
        dd = DISPLAY_DEVICE(); dd.cb = ctypes.sizeof(DISPLAY_DEVICE)
    idxs = sorted(set(idxs))
    out.append("primary"); out.extend([str(n) for n in idxs])
    return out
