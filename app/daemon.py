"""Estado do daemon cs2-resolucao.ps1, visto de fora.

O daemon segura um mutex nomeado enquanto roda. Abrir esse mutex e a
forma mais barata de saber se ele está no ar: não precisa varrer
processos nem ler linha de comando de powershell.exe.
"""

import ctypes
import os

from .constants import (
    CONFIG_FILE,
    DAEMON_MUTEX,
    DAEMON_VBS,
    LOG_FILE,
    NIRCMD_EXE,
)

_SYNCHRONIZE = 0x00100000


def is_running() -> bool:
    try:
        k32 = ctypes.windll.kernel32
        k32.OpenMutexW.restype = ctypes.c_void_p
        k32.OpenMutexW.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_wchar_p]
        handle = k32.OpenMutexW(_SYNCHRONIZE, False, DAEMON_MUTEX)
        if handle:
            k32.CloseHandle(ctypes.c_void_p(handle))
            return True
    except Exception:
        pass
    return False


def status():
    """Resumo para o indicador do cabecalho.

    A ordem importa: sem nircmd nada funciona, entao esse caso vem antes
    de reportar o daemon.
    """
    if not os.path.exists(NIRCMD_EXE):
        return "erro", "nircmd ausente", "Esperado em %s" % NIRCMD_EXE
    if not os.path.exists(CONFIG_FILE):
        return "aviso", "sem config", "Clique em aplicar para gerar o JSON"
    if is_running():
        return "ok", "daemon ativo", "Troca a resolução quando o CS2 abrir"
    return "aviso", "daemon parado", "O desktop não vai acompanhar o jogo"


def can_start() -> bool:
    return os.path.exists(DAEMON_VBS) and not is_running()


def start() -> tuple:
    """Sobe o daemon pelo .vbs, que o inicia com janela oculta."""
    if not os.path.exists(DAEMON_VBS):
        return False, "cs2-resolucao.vbs não está em %s" % os.path.dirname(DAEMON_VBS)
    try:
        os.startfile(DAEMON_VBS)  # noqa: S606 - caminho fixo, ação do usuário
    except OSError as exc:
        return False, "Não consegui iniciar o daemon: %s" % exc
    return True, "Daemon iniciado."


def tail_log(lines=40):
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            return f.read().splitlines()[-lines:]
    except OSError:
        return []


def open_log() -> tuple:
    if not os.path.exists(LOG_FILE):
        return False, "Ainda não existe log em %s" % LOG_FILE
    try:
        os.startfile(LOG_FILE)  # noqa: S606 - caminho fixo, ação do usuário
    except OSError as exc:
        return False, "Não consegui abrir o log: %s" % exc
    return True, "Log aberto."
