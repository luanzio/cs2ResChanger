# CS2ResChanger

Mantém a resolução do **desktop** igual à do **CS2** enquanto você joga, e devolve
a resolução normal quando o jogo fecha. O alt-tab passa a ser instantâneo.

![versão](https://img.shields.io/badge/vers%C3%A3o-2.0.0-f5a524)
![windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078d4)

---

## O problema que isso resolve

CS2 em **fullscreen exclusivo** numa resolução diferente da do desktop obriga o
Windows a trocar de modo de vídeo **a cada alt-tab**: 1 a 3 segundos de tela preta
e re-sync do monitor, nas duas direções.

Jogar em janela sem borda resolve o alt-tab e piora a latência. A combinação boa é
**fullscreen exclusivo + desktop na mesma resolução do jogo**: aí não existe troca
de modo nenhuma. Manter isso na mão é chato, e é o que este projeto automatiza.

---

## Como funciona

```
CS2ResChanger.exe  →  cs2-config.json  →  cs2-resolucao.ps1  →  nircmd
    (configura)         (contrato)           (executa)          (aplica)
                                                   ↑
                                   cs2-resolucao.vbs inicia o daemon
                                   oculto no login do Windows
```

O aplicativo **nunca troca resolução**. Ele só escreve dois arquivos:

| arquivo | o que recebe |
|---|---|
| `cs2_video.txt` | a resolução com que o CS2 abre, e a flag `fullscreen_min_on_focus_loss` |
| `C:\nircmd\cs2-config.json` | as resoluções de jogo e de desktop, para o daemon |

Quem aplica no Windows é o `cs2-resolucao.ps1`, um daemon que fica aguardando o
processo `cs2.exe`. Ele relê o JSON a cada partida, então **mudar valores no app
vale já no próximo jogo** — sem reiniciar nada.

---

## Instalação

### 1. NirCmd

Baixe o [NirCmd](https://www.nirsoft.net/utils/nircmd.html) e deixe o executável em:

```
C:\nircmd\nircmd.exe
```

### 2. O daemon

Copie para a mesma pasta os dois arquivos deste repositório:

```
C:\nircmd\cs2-resolucao.ps1
C:\nircmd\cs2-resolucao.vbs
```

### 3. Iniciar junto com o Windows

1. `Win + R` → `shell:startup`
2. Crie um atalho para `C:\nircmd\cs2-resolucao.vbs` dentro da pasta que abriu

O `.vbs` existe só para iniciar o PowerShell com janela oculta
(`objShell.Run ..., 0, False`). Sem ele, aparece um console preto no login.

> **Não precisa de Admin.** A API `ChangeDisplaySettings` não exige elevação —
> o daemon roda no contexto do usuário normalmente.

### 4. O aplicativo

Baixe o `.zip` em **[Releases](https://github.com/luanzio/cs2ResChanger/releases)**,
extraia e rode `CS2ResChanger.exe`.

> Se o Windows Defender acusar o `.exe`, é **falso positivo**. O PyInstaller
> `--onefile` descompacta o programa em `%TEMP%` em tempo de execução, e esse
> padrão é heurística comum de empacotador malicioso. Assinar o executável
> resolveria de vez; por enquanto, adicione a pasta extraída em
> **Segurança do Windows → Vírus e ameaças → Gerenciar configurações → Exclusões**.

---

## Usando o aplicativo

O cabeçalho mostra o monitor alvo e o estado do daemon (**ativo**, **parado**,
**nircmd ausente**). Com o daemon parado e o `.vbs` instalado, aparece um botão
para iniciar na hora.

| seção | o que faz |
|---|---|
| **Resolução de jogo** | largura, altura, Hz e BPP com que o CS2 abre. Atalhos para as resoluções mais usadas e botões para copiar do Windows, da nativa ou do próprio `cs2_video.txt`. |
| **Resolução do desktop** | para onde o Windows volta ao fechar o jogo. A lista "modos que o monitor aceita" vem direto do driver. |
| **Favoritas** | clique numa para carregar nos campos de jogo; o `×` remove. |
| **Não minimizar no alt-tab** | alterna `fullscreen_min_on_focus_loss`. Em `0`, o arquivo volta a somente-leitura para o CS2 não reescrever por cima. |
| **APLICAR E SALVAR** | grava o `cs2_video.txt` e o `cs2-config.json`. Avisa se o monitor não aceitar o modo escolhido. |

---

## O `cs2-config.json`

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

`monitor` aceita `"primary"` ou o número do display (`"1"`, `"2"`). O daemon
recusa o arquivo se faltar qualquer campo, e registra o motivo em
`C:\nircmd\cs2-resolucao.log`.

---

## Por que o `-updatereg` é obrigatório

Esta é a parte que parece detalhe e é o mecanismo central.

```
COM -updatereg:   registro = 1280x960
                  alt-tab → CS2 solta o fullscreen exclusivo
                          → Windows aplica o modo do registro = 1280x960
                          → MESMO modo, nada acontece, instantâneo

SEM -updatereg:   registro = 1920x1080 (só a sessão está em 1280x960)
                  alt-tab → Windows volta pro registro = 1920x1080   ← troca
                  volta pro jogo → CS2 reaplica 1280x960             ← troca
```

Sem `-updatereg` o alt-tab pisca nas duas direções, que é exatamente o problema
que o projeto existe para resolver.

**Efeito colateral:** se a máquina travar ou desligar no meio da partida, o
registro fica com a resolução do jogo e o desktop nasce em 4:3 no próximo boot.
A v2 corrige sozinha — veja *auto-reparo* no [CHANGELOG](CHANGELOG.md).

---

## Por que não um wrapper `%command%` do Steam

É a primeira ideia de todo mundo que olha o projeto: sem processo residente, sem
poll. Foi tentada e abandonada, por dois motivos que a matam:

1. **Abre uma janela de console.** O Steam executa o `.cmd` com console anexado, e
   não há como suprimir isso de forma confiável de dentro do próprio batch.
2. **Só funciona abrindo pelo Steam.** Atalho direto para o `cs2.exe` ignora as
   opções de inicialização. O daemon funciona de qualquer jeito, porque vigia o
   processo.

---

## Novidades da v2

Resumo; o detalhe está no [CHANGELOG.md](CHANGELOG.md).

- **Interface nova**, escura, em alto DPI, com widgets desenhados em vez de ttk
- **Zero CPU durante a partida**: `WaitForExit()` no lugar do poll de 2 em 2 s
- **Auto-reparo no boot** se o desktop ficou preso na resolução do jogo
- Espera a janela do jogo existir antes de trocar o modo
- Detecta o Steam pelo registro, não só em `Program Files (x86)`
- Lista os modos que o monitor realmente aceita e avisa quando o escolhido não está nela

---

## FAQ

**“cs2_video.txt não encontrado”**
Abra o CS2 pelo menos uma vez. O app procura o Steam pelo registro e em
`Program Files`, e usa a conta mais recente quando há várias.

**O daemon aparece como parado mesmo rodando**
O indicador olha um mutex nomeado. Se o daemon subiu por uma versão antiga do
script, o nome não bate — substitua o `.ps1` pelo desta versão.

**Monitor errado**
Troque o monitor no cabeçalho do app, ou o campo `"monitor"` no JSON.

**Troquei a resolução no app, preciso reiniciar alguma coisa?**
Não. O daemon relê o JSON a cada partida. Só vale reiniciar o daemon se você
alterar o **`.ps1`** em si.

**Preciso rodar como Admin?**
Não.

---

## Build local

```bash
pip install -r requirements.txt
```

```bash
pyinstaller --noconsole --onefile --name CS2ResChanger --icon assets/cs2.ico --add-data "assets/cs2.ico;assets" main.py
```

Saída em `dist/CS2ResChanger.exe`.

---

## Estrutura

```
cs2ResChanger/
├─ app/
│  ├─ app.py            janela principal
│  ├─ widgets.py        Card, Button, Input, Select, Chip, Switch, Toast
│  ├─ theme.py          paleta, fontes, DPI, cantos arredondados
│  ├─ display_api.py    EnumDisplaySettings / EnumDisplayDevices
│  ├─ cs2_file.py       cs2_video.txt
│  ├─ config_store.py   cs2-config.json
│  ├─ daemon.py         estado do daemon
│  └─ constants.py
├─ assets/cs2.ico
├─ cs2-resolucao.ps1    daemon
├─ cs2-resolucao.vbs    inicia o daemon oculto
├─ main.py
├─ requirements.txt
└─ .github/workflows/release.yml
```

Referência do passo a passo manual original:
[vídeo](https://www.youtube.com/watch?v=YCoyxFt2gSY).
