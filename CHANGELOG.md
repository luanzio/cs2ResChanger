# Changelog

## 2.1.0 — 2026-10-22

### Digital vibrance (NVIDIA)

Mesmo ciclo da resolução: um nível durante a partida, outro ao fechar o jogo,
aplicado **só no monitor do campo `monitor`**. Três campos novos e opcionais no
`cs2-config.json` — `vibranceEnabled`, `vibranceGame`, `vibranceDesktop` — que
um JSON de versão anterior simplesmente não tem, e aí o daemon ignora o recurso.

- **Vem desligado.** Ligar faz o daemon assumir o controle do DVC daquele
  monitor; quem já ajusta esse valor por fora não ia querer isso acontecendo
  sozinho depois de uma atualização.
- Escala **0–100 com padrão 50**, a mesma do Painel de Controle da NVIDIA. A
  `NvAPI_GetDVCInfo` antiga é 0–63 com 0 = sem boost, e mostraria um número que
  não bate com o do painel; o código usa a variante `Ex`.
- O handle da NVAPI é casado com o nome de device (`\\.\DISPLAYn`) por
  `NvAPI_GetAssociatedNvidiaDisplayName`, e reenumerado a cada chamada — depois
  de uma troca de modo ou hotplug o handle antigo pode não valer mais.
- Aplicado **depois** da troca de resolução, porque uma mudança de modo de vídeo
  pode reiniciar o DVC.
- O daemon reaplica o nível de desktop ao subir: o driver guarda o DVC entre
  sessões, então um travamento no meio da partida deixaria o nível de jogo preso.
- Não precisa de Admin, e não precisa de binário externo: usa a `nvapi64.dll`
  que já vem com o driver.
- Degrada em silêncio. A NVAPI não exporta as funções por nome — expõe um
  `nvapi_QueryInterface(id)` cujos ids vêm de engenharia reversa. Se qualquer
  passo falhar, o daemon loga um aviso e segue trocando resolução; no app a
  seção nem aparece.

### Interface

- Seção nova com uma chave liga/desliga e dois sliders, com o valor que está
  ativo na placa mostrado ao lado
- Botão **Testar** em cada slider, que aplica na hora para dar para ver a cor
- Widget `Slider` novo em `app/widgets.py`

---

## 2.0.0 — 2026-10-22

A arquitetura **não muda**: o daemon PowerShell continua sendo o motor certo, e o
aplicativo continua só escrevendo arquivos. O que muda é a interface e um conjunto
de correções dentro do daemon.

### Interface

Reescrita do zero. O `ttk` no Windows pega botão, campo e combobox do visual style
nativo e ignora cor de fundo, então não existe tema escuro de verdade com ele. Os
widgets agora são desenhados em `Canvas` (`app/widgets.py`), com cantos
arredondados em antialias via Pillow e fallback vetorial quando o Pillow falta.

- Tema escuro com a barra de título do Windows em modo escuro
- Consciente de DPI (`SetProcessDpiAwareness`), fontes em pixels — sem borrão em 125/150%
- Três indicadores no topo: resolução atual do Windows, nativa do monitor e a configurada no CS2
- **Indicador de estado do daemon** no cabeçalho, com botão para iniciar quando está parado
- Favoritas viraram pílulas: clique carrega, `×` remove
- As `messagebox` do Windows deram lugar a avisos flutuantes
- Seletor de monitor mostra o **nome da tela**, não o da placa de vídeo
- Lista dos modos que o monitor aceita, lida do driver
- Aviso ao salvar quando o monitor não lista a resolução ou os Hz escolhidos
- A chave `fullscreen_min_on_focus_loss` virou uma chave liga/desliga que **mostra o
  estado real** do arquivo, em vez de alternar às cegas

### Daemon (`cs2-resolucao.ps1`)

#### 1. `WaitForExit()` no lugar do poll

A v1 chamava `Get-Process` de 2 em 2 segundos **durante a partida inteira**. A v2
detecta o jogo, bloqueia em `WaitForExit()` e não acorda nenhuma vez até ele fechar.

Medido numa instalação real: a v1 tinha acumulado **46 segundos de CPU** em ~29 h de
uptime, quase tudo no poll durante o jogo.

#### 2. Auto-reparo no boot

Se o daemon sobe e encontra o desktop na resolução do jogo **sem o jogo rodando**, a
sessão anterior travou. Ele restaura sozinho. Como o daemon inicia no login, isso
conserta automaticamente o efeito colateral do `-updatereg`.

#### 3. Espera a janela do jogo existir

A v1 trocava a resolução no instante em que o processo `cs2.exe` aparecia — no meio
da inicialização, disputando a troca de modo com o próprio jogo. A v2 espera o
`MainWindowHandle`, com timeout de 40 s.

#### 4. `EnumDisplaySettings` em vez de `System.Windows.Forms.Screen`

Aquela classe cacheia a lista de telas pela vida do processo. Num daemon de longa
duração ela devolve para sempre o modo que estava ativo quando o processo subiu, o
que fazia a verificação falhar sempre e aplicar o modo duas vezes por partida.

#### 5. Correções de P/Invoke

- A `DEVMODE` era declarada em **Ansi** (156 bytes) com `dmSize = 220`, que é o
  tamanho da versão **Unicode**. A API escrevia além do buffer. Agora é `DEVMODEW`,
  com o tamanho vindo de `Marshal.SizeOf`.
- A verificação olhava `\\.\DISPLAY1` fixo, ou seja, **o monitor errado** quando o
  config apontava para o 2. Agora resolve o device a partir do campo `monitor`, e
  `"primary"` é resolvido enumerando os adaptadores.

#### 6. Mutex de instância única em `Local\`

Era `Global\`, que exige `SeCreateGlobalPrivilege`. O token filtrado de um usuário
não elevado não tem esse privilégio, então o construtor lançava exceção e **matava o
daemon** — justamente no cenário normal de uso, sem Admin. O daemon é um por sessão
de logon, então `Local\` é o escopo certo. A criação também virou `try/catch`: sem
mutex ele segue sem a trava em vez de morrer.

#### 7. Robustez

- Valida `nircmd.exe` e todos os campos do JSON antes de começar
- Confirma se o modo aplicou de verdade, com uma segunda tentativa se não
- `finally` restaura o desktop se o script for morto com o jogo aberto
- Log com rotação em `C:\nircmd\cs2-resolucao.log`
- Sem acentos no código: `.ps1` em UTF-8 sem BOM é lido como ANSI pelo PowerShell 5.1

### Aplicativo (Python)

- Steam localizado pelo **registro** (`HKCU\Software\Valve\Steam`), com
  `Program Files` como fallback. Antes só olhava `Program Files (x86)`, o que
  quebrava em quem instalou o Steam noutro disco.
- Com várias contas Steam na máquina, usa o `cs2_video.txt` mais recente
- `cs2_file.py` não abre mais janela: devolve `(ok, mensagem)` e quem chama decide
- `cs2-config.json` gravado por arquivo temporário + `os.replace`, para não corromper
  se o daemon estiver lendo na mesma hora
- `load_config()` completa as chaves que faltam — o daemon recusa JSON incompleto
- `cs2-resolucao.vbs` passou a fazer parte do repositório; a documentação dependia
  dele e ele não estava versionado

### Documentação

- Explica **por que** o projeto existe (troca de modo de vídeo no alt-tab)
- Explica por que o `-updatereg` é obrigatório e qual o efeito colateral
- Registra por que o wrapper `%command%` do Steam foi abandonado
- Removido **“rode o PS1 como Admin”**: `ChangeDisplaySettings` não exige elevação
- Removido **“reinicie o script ou o PC após editar”**: o script relê o JSON a cada
  partida. Só vale reiniciar o daemon se o `.ps1` em si mudar.
- Motivo técnico do falso positivo do Defender

---

## 1.0.0

Primeira versão: GUI em Tkinter/ttk, `cs2_video.txt`, `cs2-config.json`, favoritas e
o daemon PowerShell com poll.
