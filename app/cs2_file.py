"""Leitura e escrita do cs2_video.txt.

Nenhuma funcao daqui abre janela: todas devolvem (ok, mensagem) e quem
chama decide como mostrar. A GUI mostra em toast.
"""

import os
import re

NOT_FOUND = "cs2_video.txt não encontrado. Abra o CS2 ao menos uma vez."

_RE_W = r'"setting\.defaultres"\s+"(\d+)"'
_RE_H = r'"setting\.defaultresheight"\s+"(\d+)"'
_RE_FOCUS = r'"setting\.fullscreen_min_on_focus_loss"\s+"(\d+)"'


def _steam_roots():
    """Candidatos a raiz do Steam, do mais confiável para o menos.

    A versão antiga olhava só Program Files (x86), o que quebra em quem
    instalou o Steam em outro disco.
    """
    roots = []

    try:
        import winreg
        for hive, key, name in (
            (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
        ):
            try:
                with winreg.OpenKey(hive, key) as k:
                    val, _ = winreg.QueryValueEx(k, name)
                    if val:
                        roots.append(os.path.normpath(val))
            except OSError:
                continue
    except Exception:
        pass

    roots.append(r"C:\Program Files (x86)\Steam")
    roots.append(r"C:\Program Files\Steam")

    out = []
    for r in roots:
        if r and r not in out and os.path.isdir(r):
            out.append(r)
    return out


def find_video_cfg():
    """Caminho do cs2_video.txt, ou None.

    Quando ha mais de uma conta Steam na maquina, usa a mais recente.
    """
    found = []
    for root in _steam_roots():
        userdata = os.path.join(root, "userdata")
        if not os.path.isdir(userdata):
            continue
        try:
            users = os.listdir(userdata)
        except OSError:
            continue
        for user_id in users:
            path = os.path.join(userdata, user_id, "730", "local", "cfg", "cs2_video.txt")
            if os.path.exists(path):
                try:
                    found.append((os.path.getmtime(path), path))
                except OSError:
                    found.append((0, path))
    if not found:
        return None
    found.sort(reverse=True)
    return found[0][1]


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _unlock(path):
    try:
        os.chmod(path, 0o666)
    except OSError:
        pass


def _apply_lock(path, focus_value):
    """focus_loss 0 e o estado que o jogador quer manter, entao o arquivo
    volta a somente-leitura para o CS2 não reescrever por cima."""
    try:
        os.chmod(path, 0o444 if focus_value == "0" else 0o666)
    except OSError:
        pass


def get_current_resolution_from_cs2():
    path = find_video_cfg()
    if not path:
        return None, None
    try:
        content = _read(path)
    except OSError:
        return None, None
    w, h = re.search(_RE_W, content), re.search(_RE_H, content)
    if w and h:
        return w.group(1), h.group(1)
    return None, None


def read_focus_loss():
    """(valor, somente_leitura). valor e '0', '1' ou None se não existir."""
    path = find_video_cfg()
    if not path:
        return None, False
    try:
        content = _read(path)
    except OSError:
        return None, False
    m = re.search(_RE_FOCUS, content)
    readonly = not os.access(path, os.W_OK)
    return (m.group(1) if m else None), readonly


def change_resolution(new_width, new_height):
    path = find_video_cfg()
    if not path:
        return False, NOT_FOUND

    _unlock(path)
    try:
        content = _read(path)
    except OSError as exc:
        return False, "Falha ao ler cs2_video.txt: %s" % exc

    focus = re.search(_RE_FOCUS, content)
    focus_val = focus.group(1) if focus and focus.group(1) in ("0", "1") else "0"

    content, n_w = re.subn(_RE_W, '"setting.defaultres" "%s"' % new_width, content)
    content, n_h = re.subn(_RE_H, '"setting.defaultresheight" "%s"' % new_height, content)
    if not (n_w and n_h):
        _apply_lock(path, focus_val)
        return False, "cs2_video.txt sem as chaves de resolução. Abra o CS2 uma vez."

    try:
        _write(path, content)
    except OSError as exc:
        return False, "Falha ao gravar cs2_video.txt: %s" % exc
    _apply_lock(path, focus_val)
    return True, "CS2 agora abre em %sx%s." % (new_width, new_height)


def toggle_focus_loss_setting():
    """Inverte fullscreen_min_on_focus_loss. Devolve (ok, msg, novo_valor)."""
    path = find_video_cfg()
    if not path:
        return False, NOT_FOUND, None

    _unlock(path)
    try:
        content = _read(path)
    except OSError as exc:
        return False, "Falha ao ler cs2_video.txt: %s" % exc, None

    match = re.search(_RE_FOCUS, content)
    if not match:
        anchor = re.search(_RE_H, content)
        addition = '\n\t\t"setting.fullscreen_min_on_focus_loss"\t\t"0"'
        if anchor:
            content = content.replace(anchor.group(0), anchor.group(0) + addition)
        else:
            content = content.strip() + addition + "\n"
        new_val = "0"
    else:
        new_val = "1" if match.group(1) == "0" else "0"
        content = re.sub(
            _RE_FOCUS,
            '"setting.fullscreen_min_on_focus_loss" "%s"' % new_val,
            content,
        )

    try:
        _write(path, content)
    except OSError as exc:
        return False, "Falha ao gravar cs2_video.txt: %s" % exc, None
    _apply_lock(path, new_val)

    if new_val == "0":
        msg = "CS2 não minimiza mais no alt-tab. Arquivo protegido."
    else:
        msg = "CS2 volta a minimizar no alt-tab. Arquivo liberado."
    return True, msg, new_val
