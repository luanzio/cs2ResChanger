# CS2ResChanger

Ferramenta para **gerenciar resoluções no CS2** de forma simples, com GUI (Tkinter) + automação opcional via **NirCmd + PowerShell**.

---

## ▶️ Primeiro: siga este vídeo

Antes de usar o CS2ResChanger, **assista e configure** seguindo este vídeo (passo a passo manual do PS1 + NirCmd):

👉 https://www.youtube.com/watch?v=YCoyxFt2gSY

Depois, **volte aqui** e use o **CS2ResChanger** para não precisar editar valores na mão sempre.

---

## O que o CS2ResChanger faz

- Lê/mostra **resolução atual** do Windows e **nativa** do monitor.
- Configura a resolução do **CS2** (edita `cs2_video.txt`).
- **Alterna** a flag `fullscreen_min_on_focus_loss` (com proteção/desproteção do arquivo).
- **Gerencia favoritas** (ex.: `1280x960@240`) e aplica com um clique.
- Define a **resolução do Windows para restaurar ao fechar o jogo** (usado pelo script PS1).
- Mantém o JSON em `C:\nircmd\cs2-config.json` atualizado para o script PS1 (NirCmd).

---

## Download

- Baixe o `.zip` da aba **Releases**:
  👉 [Clique aqui para acessar as Releases](https://github.com/luanzio/cs2ResChanger/releases)

- Extraia tudo e rode `CS2ResChanger.exe`.

**Importante**: se o Windows Defender acusar o `.exe` como vírus, isso é um **falso positivo** (por ser novo e não assinado). Veja abaixo como contornar:

### Se o antivírus bloquear:
- Extraia o `.zip` em uma pasta
- Vá em **Segurança do Windows** → **Vírus e ameaças** → **Gerenciar configurações** → **Exclusões**
- Adicione a pasta extraída como exceção
---

## Integração: NirCmd + PowerShell

### Pré-requisitos
- **NirCmd** em `C:\nircmd\nircmd.exe`.
- O app cria/atualiza `C:\nircmd\cs2-config.json`.

### JSON de exemplo (`C:\nircmd\cs2-config.json`)
```json
{
  "resWidth": 1280,
  "resHeight": 960,
  "resHz": 240,
  "resBPP": 32,
  "monitor": "primary",
  "defaultWidth": 1920,
  "defaultHeight": 1080,
  "defaultHz": 240,
  "favorites": ["1280x960@240"]
}
```

### Script PowerShell (`cs2-resolucao.ps1`)
Você deve trocar o script do vídeo por **este**, ele recarrega o JSON antes de aplicar/restaurar e funciona dinamicamente com as resoluções setadas sem precisar reiniciar:

```powershell
$nirCmd = "C:\nircmd\nircmd.exe"
$configPath = "C:\nircmd\cs2-config.json"
$gameProcess = "cs2"

function Load-Config {
    Get-Content $configPath -Raw | ConvertFrom-Json
}

function Set-Resolution([string]$monitor, [int]$w, [int]$h, [int]$b, [int]$hz) {
    & $nirCmd setdisplay "monitor:$monitor" $w $h $b $hz -updatereg
}

while ($true) {
    while (-not (Get-Process -Name $gameProcess -ErrorAction SilentlyContinue)) {
        Start-Sleep -Seconds 1
    }

    $cfg = Load-Config
    Write-Output "$gameProcess detectado. Alterando para $($cfg.resWidth)x$($cfg.resHeight)@$($cfg.resHz) (bpp $($cfg.resBPP))..."
    Set-Resolution $cfg.monitor $cfg.resWidth $cfg.resHeight $cfg.resBPP $cfg.resHz

    while (Get-Process -Name $gameProcess -ErrorAction SilentlyContinue) {
        Start-Sleep -Seconds 2
    }

    $cfg = Load-Config
    Write-Output "$gameProcess fechado. Restaurando para $($cfg.defaultWidth)x$($cfg.defaultHeight)@$($cfg.defaultHz) (bpp $($cfg.resBPP))..."
    Set-Resolution $cfg.monitor $cfg.defaultWidth $cfg.defaultHeight $cfg.resBPP $cfg.defaultHz

    Start-Sleep -Seconds 2
}
```

**Importante:** se você **trocar/editar** esse script do PowerShell, **reinicie o script** (feche e abra o `.ps1`) **ou reinicie o computador** para garantir que o Agendador de Tarefas/inicialização aplique a versão nova.

---

## Como usar (GUI)
1. Abra `CS2ResChanger.exe`.
2. **Monitor & Sistema**: clique em **Atualizar/Detectar** para ver resolução atual e nativa.
3. **CS2 (cs2_video.txt)**:
   - Preencha **Largura/Altura/Hz/BPP** ou use:
     - **Usar resolução atual do Windows**
     - **Usar resolução nativa do monitor**
     - **Detectar do cs2_video.txt**
     - **Usar favorita selecionada**
   - Clique **APLICAR E SALVAR**.
   - Se quiser, use **Alternar Focus Loss (cs2_video.txt)**.
4. **Windows — Resolução ao sair do jogo**: defina a resolução para restaurar quando o CS2 fechar.
5. **Favoritas**:
   - **Salvar atual (CS2) como favorita**
   - **Remover selecionada**
   - Selecione no combo e use **Usar favorita selecionada** na caixa do CS2.

---

## Build local do .exe (dev)

Pré-requisito:
```bash
pip install -r requirements.txt
```

Gerar **onefile** com ícone:
```bash
pyinstaller --noconsole --onefile --name CS2ResChanger --icon assets/cs2.ico --add-data "assets\cs2.ico;assets" main.py
```

Saída: `dist/CS2ResChanger.exe`

---

## Estrutura sugerida do repositório

```
CS2ResChanger/
├─ app/
│  ├─ app.py
│  ├─ config_store.py
│  ├─ constants.py
│  ├─ cs2_file.py
│  └─ display_api.py
├─ assets/
│  └─ cs2.ico
├─ cs2-resolucao.ps1
├─ main.py
├─ requirements.txt
└─ .github/workflows/release.yml
```

---

## FAQ

- **“cs2_video.txt não encontrado”** → abra o CS2 pelo menos uma vez.
- **Script não aplica/retorna resolução** → rode o PS1 como **Admin**; verifique NirCmd em `C:\nircmd\nircmd.exe`.
- **Monitor errado** → no JSON, troque `"monitor": "primary"` por `"1"` ou `"2"`.
- **Troquei o `.ps1` e nada mudou** → **reinicie o script** ou **reinicie o PC**.
- **Antivírus** → pode dar falso positivo com PyInstaller; crie exceção para a pasta.

---
