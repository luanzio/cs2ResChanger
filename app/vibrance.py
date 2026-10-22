"""Digital vibrance pela NVAPI, sempre num monitor especifico.

A NVAPI não exporta as funções por nome: exporta um único
`nvapi_QueryInterface(id)` que devolve o ponteiro de cada uma. Os ids são
valores internos, conhecidos por engenharia reversa e estáveis há muitos
anos, mas sem garantia da NVIDIA. Tudo aqui degrada em silêncio: se
qualquer passo falhar, `available()` devolve False e o app esconde a seção.

Usa a variante Ex, de escala 0-100 com padrão 50 — a mesma do slider do
Painel de Controle da NVIDIA. A `GetDVCInfo` antiga é 0-63 com 0 = sem
boost, o que mostraria um número que não bate com o do painel.
"""

import ctypes

from .display_api import _get_device_name

_ID_INIT = 0x0150E828
_ID_UNLOAD = 0xD22BDD7E
_ID_ENUM = 0x9ABDD40D
_ID_NAME = 0x22A78B05
_ID_GET_EX = 0x0E45002D
_ID_SET_EX = 0x4A82C2B1

_VERSION = 20 | (1 << 16)  # sizeof(NV_DISPLAY_DVC_INFO_EX) | (versão << 16)


class _DvcEx(ctypes.Structure):
    _fields_ = [
        ("version", ctypes.c_uint32),
        ("current", ctypes.c_int32),
        ("minimum", ctypes.c_int32),
        ("maximum", ctypes.c_int32),
        ("default_", ctypes.c_int32),
    ]


_P_SIMPLE = ctypes.CFUNCTYPE(ctypes.c_int)
_P_ENUM = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p))
_P_NAME = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_char_p)
_P_DVC = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32,
                          ctypes.POINTER(_DvcEx))


class _Api:
    """Carrega a nvapi64.dll uma vez e guarda os ponteiros resolvidos."""

    def __init__(self):
        self.ok = False
        try:
            dll = ctypes.WinDLL("nvapi64.dll")
            query = dll.nvapi_QueryInterface
            query.restype = ctypes.c_void_p
            query.argtypes = [ctypes.c_uint32]

            def fn(proto, api_id):
                ptr = query(api_id)
                return proto(ptr) if ptr else None

            self.init = fn(_P_SIMPLE, _ID_INIT)
            self.unload = fn(_P_SIMPLE, _ID_UNLOAD)
            self.enum = fn(_P_ENUM, _ID_ENUM)
            self.name = fn(_P_NAME, _ID_NAME)
            self.get = fn(_P_DVC, _ID_GET_EX)
            self.set = fn(_P_DVC, _ID_SET_EX)
        except Exception:
            return

        if not all((self.init, self.enum, self.name, self.get, self.set)):
            return
        try:
            if self.init() != 0:
                return
        except Exception:
            return
        self.ok = True

    def handle(self, device):
        """Handle da NVAPI cujo nome associado bate com \\\\.\\DISPLAYn."""
        if not device:
            return None
        for index in range(16):
            h = ctypes.c_void_p()
            try:
                if self.enum(index, ctypes.byref(h)) != 0:
                    break
                buf = ctypes.create_string_buffer(64)
                if self.name(h, buf) != 0:
                    continue
            except Exception:
                return None
            if buf.value.decode("ascii", "ignore").lower() == device.lower():
                return h
        return None


_api = None


def _get_api():
    global _api
    if _api is None:
        _api = _Api()
    return _api


def available() -> bool:
    return _get_api().ok


def info(monitor: str = "primary"):
    """{'current','minimum','maximum','default'} ou None."""
    api = _get_api()
    if not api.ok:
        return None
    h = api.handle(_get_device_name(monitor))
    if h is None:
        return None
    data = _DvcEx(version=_VERSION)
    try:
        if api.get(h, 0, ctypes.byref(data)) != 0:
            return None
    except Exception:
        return None
    return {
        "current": int(data.current),
        "minimum": int(data.minimum),
        "maximum": int(data.maximum),
        "default": int(data.default_),
    }


def get_level(monitor: str = "primary"):
    data = info(monitor)
    return data["current"] if data else None


def set_level(monitor: str, level: int):
    """Aplica agora, só para o botão de teste da GUI.

    Em jogo quem aplica é o daemon — o app continua escrevendo apenas o
    cs2-config.json. Devolve (ok, mensagem).
    """
    api = _get_api()
    if not api.ok:
        return False, "NVAPI indisponível."
    device = _get_device_name(monitor)
    h = api.handle(device)
    if h is None:
        return False, "Monitor %s não encontrado pela NVAPI." % monitor

    data = _DvcEx(version=_VERSION)
    try:
        if api.get(h, 0, ctypes.byref(data)) != 0:
            return False, "Não consegui ler o vibrance atual."
        level = max(int(data.minimum), min(int(data.maximum), int(level)))
        write = _DvcEx(version=_VERSION, current=level)
        if api.set(h, 0, ctypes.byref(write)) != 0:
            return False, "A NVAPI recusou o valor."
    except Exception as exc:
        return False, "Falha na NVAPI: %s" % exc
    return True, "Vibrance em %d%% no monitor %s." % (level, monitor)
