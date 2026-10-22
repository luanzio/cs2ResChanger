# ============================================================
#  cs2-resolucao.ps1  (v2)
#
#  Troca a resolucao do desktop quando o CS2 abre e restaura
#  quando fecha, para que o alt-tab nao force troca de modo
#  de video.
#
#  Mesma arquitetura da v1 (daemon iniciado oculto pelo .vbs
#  no login), com as correcoes listadas no CHANGELOG.md:
#
#   - WaitForExit() em vez de poll: ZERO CPU durante a partida.
#     Era a maior parte do custo da v1.
#   - auto-reparo no boot: se o script sobe e o desktop esta na
#     resolucao do jogo sem o jogo rodando (travou na partida
#     anterior), restaura sozinho.
#   - espera a janela do jogo existir antes de trocar, para nao
#     disputar a troca de modo com a inicializacao do jogo.
#   - mutex de instancia unica (por sessao de logon).
#   - restaura no finally, mesmo com erro.
#   - valida nircmd e JSON antes de rodar; log com rotacao.
#   - sem acentos: .ps1 em UTF-8 sem BOM e lido como ANSI pelo
#     PowerShell 5.1, o que gerava "resolucao" quebrada na v1.
#
#  MANTEM o -updatereg de proposito. Ele e o mecanismo: grava o
#  modo no registro, entao quando o CS2 solta o fullscreen
#  exclusivo no alt-tab o Windows volta para o MESMO modo e nao
#  ha troca nenhuma. Sem isso o alt-tab pisca a cada ida e volta.
#
#  NAO precisa de Admin: ChangeDisplaySettings nao exige elevacao.
#  NAO precisa reiniciar nada ao mudar resolucao no app: o config
#  e relido a cada partida.
# ============================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$NirCmd      = 'C:\nircmd\nircmd.exe'
$ConfigPath  = 'C:\nircmd\cs2-config.json'
$LogPath     = 'C:\nircmd\cs2-resolucao.log'
$GameProcess = 'cs2'
$MaxLogKB    = 256
$MutexName   = 'Local\cs2-resolucao-v2'

function Write-Log {
    param([string]$Message, [string]$Level = 'INFO')
    $line = '{0} [{1}] {2}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Level, $Message
    try {
        if ((Test-Path $LogPath) -and ((Get-Item $LogPath).Length -gt ($MaxLogKB * 1KB))) {
            Move-Item $LogPath "$LogPath.old" -Force
        }
        Add-Content -Path $LogPath -Value $line -Encoding UTF8
    } catch { }
}

function Get-Config {
    if (-not (Test-Path $ConfigPath)) { throw "Config nao encontrado: $ConfigPath" }
    $cfg = ConvertFrom-Json (Get-Content $ConfigPath -Raw)
    foreach ($field in 'resWidth','resHeight','resHz','resBPP','monitor',
                       'defaultWidth','defaultHeight','defaultHz') {
        if (-not $cfg.PSObject.Properties.Name.Contains($field)) {
            throw "Campo ausente no config: $field"
        }
    }
    return $cfg
}

# ATENCAO: nao usar [System.Windows.Forms.Screen] aqui.
# Aquela classe cacheia a lista de telas pela vida do processo, entao num
# daemon de longa duracao ela devolve para sempre o modo que estava ativo
# quando o processo subiu. Isso fazia a verificacao falhar sempre e disparar
# um retry desnecessario, aplicando o modo duas vezes a cada partida.
# EnumDisplaySettings consulta o driver na hora e nao tem cache.
#
# A struct abaixo e a DEVMODEW (Unicode, 220 bytes). Em Ansi ela tem 156, e
# informar dmSize=220 num buffer de 156 deixa a API escrever fora do buffer.
Add-Type @'
using System;
using System.Runtime.InteropServices;
[StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
public struct CS2DM {
  [MarshalAs(UnmanagedType.ByValTStr, SizeConst=32)] public string dn;
  public short sv, dv, size, extra;
  public int fields, px, py, ori, fo;
  public short color, duplex, yres, tt, coll;
  [MarshalAs(UnmanagedType.ByValTStr, SizeConst=32)] public string fn;
  public short lp;
  public int bpp, w, h, flags, freq;
  public int icm, intent, media, dither, r1, r2, pw, ph;
}
[StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
public struct CS2DD {
  public int cb;
  [MarshalAs(UnmanagedType.ByValTStr, SizeConst=32)]  public string name;
  [MarshalAs(UnmanagedType.ByValTStr, SizeConst=128)] public string str;
  public int flags;
  [MarshalAs(UnmanagedType.ByValTStr, SizeConst=128)] public string id;
  [MarshalAs(UnmanagedType.ByValTStr, SizeConst=128)] public string key;
}
public class CS2Disp {
  [DllImport("user32.dll", CharSet=CharSet.Unicode)]
  public static extern bool EnumDisplaySettingsW(string dev, int mode, ref CS2DM dm);
  // dev como IntPtr para poder passar NULL de verdade: "" nao enumera nada
  [DllImport("user32.dll", CharSet=CharSet.Unicode)]
  public static extern bool EnumDisplayDevicesW(IntPtr dev, int num, ref CS2DD dd, int flags);
}
'@ -ErrorAction SilentlyContinue

# Traduz o campo "monitor" do config num nome de device do Windows.
#
# "primary" tem que virar um nome concreto. Passar $null para a API
# significaria "o display atual", mas o PowerShell converte $null em
# string vazia ao bindar um parametro [string], e ali a chamada falha.
# Entao resolvemos o primario enumerando os devices.
#
# A v1 verificava sempre \\.\DISPLAY1, ou seja, olhava o monitor errado
# quando o config apontava para o 2.
function Resolve-Device {
    param([string]$Monitor)

    if ($Monitor -match '^\d+$') { return "\\.\DISPLAY$Monitor" }
    if (-not [string]::IsNullOrWhiteSpace($Monitor) -and $Monitor -ne 'primary') {
        return $Monitor
    }

    $PRIMARY = 0x4
    for ($i = 0; $i -lt 16; $i++) {
        $dd = New-Object CS2DD
        $dd.cb = [System.Runtime.InteropServices.Marshal]::SizeOf([type]'CS2DD')
        if (-not [CS2Disp]::EnumDisplayDevicesW([IntPtr]::Zero, $i, [ref]$dd, 0)) { break }
        if ($dd.flags -band $PRIMARY) { return $dd.name }
    }
    return '\\.\DISPLAY1'
}

function Get-CurrentMode {
    param([string]$Monitor = 'primary')
    try {
        $dm = New-Object CS2DM
        $dm.size = [int16][System.Runtime.InteropServices.Marshal]::SizeOf([type]'CS2DM')
        if ([CS2Disp]::EnumDisplaySettingsW((Resolve-Device $Monitor), -1, [ref]$dm)) {
            return [PSCustomObject]@{ W = $dm.w; H = $dm.h; Hz = $dm.freq }
        }
        return $null
    } catch { return $null }
}

function Set-Resolution {
    param([string]$Monitor, [int]$W, [int]$H, [int]$Bpp, [int]$Hz)

    # -updatereg e obrigatorio: ver o comentario no topo do arquivo
    & $NirCmd setdisplay "monitor:$Monitor" $W $H $Bpp $Hz -updatereg
    Start-Sleep -Milliseconds 400

    $actual = Get-CurrentMode $Monitor
    if ($actual -and ($actual.W -ne $W -or $actual.H -ne $H)) {
        Write-Log "modo nao aplicou ($($actual.W)x$($actual.H)), tentando de novo" 'WARN'
        & $NirCmd setdisplay "monitor:$Monitor" $W $H $Bpp $Hz -updatereg
        Start-Sleep -Milliseconds 600
    }
}

function Restore-Desktop {
    param($Cfg)
    Write-Log ("desktop -> {0}x{1}@{2}" -f $Cfg.defaultWidth, $Cfg.defaultHeight, $Cfg.defaultHz)
    Set-Resolution $Cfg.monitor $Cfg.defaultWidth $Cfg.defaultHeight $Cfg.resBPP $Cfg.defaultHz
}

# ---- instancia unica -------------------------------------------------
# Namespace Local\ de proposito: Global\ exige SeCreateGlobalPrivilege,
# que o token filtrado de um usuario nao elevado nao tem, e ali o
# construtor lancaria excecao e mataria o daemon. O daemon e um por
# sessao de logon, entao Local\ e exatamente o escopo certo.
$mutex = $null
try {
    $mutex = New-Object System.Threading.Mutex($false, $MutexName)
    if (-not $mutex.WaitOne(0)) {
        Write-Log 'outra instancia ja esta rodando, saindo' 'WARN'
        exit 0
    }
} catch {
    Write-Log "mutex indisponivel, seguindo sem trava: $($_.Exception.Message)" 'WARN'
    $mutex = $null
}

# ---- pre-flight ------------------------------------------------------
try {
    if (-not (Test-Path $NirCmd)) { throw "nircmd nao encontrado: $NirCmd" }
    $cfg = Get-Config
    Write-Log 'iniciado'
} catch {
    Write-Log "falha no pre-flight: $($_.Exception.Message)" 'ERRO'
    if ($mutex) { try { $mutex.ReleaseMutex() } catch { } }
    exit 1
}

# ---- auto-reparo: sobrou resolucao de jogo de uma sessao travada? ----
try {
    $cur = Get-CurrentMode $cfg.monitor
    $jogoRodando = [bool](Get-Process -Name $GameProcess -ErrorAction SilentlyContinue)
    if ($cur -and -not $jogoRodando -and
        $cur.W -eq $cfg.resWidth -and $cur.H -eq $cfg.resHeight) {
        Write-Log 'desktop estava na resolucao do jogo sem o jogo rodando, reparando' 'WARN'
        Restore-Desktop $cfg
    }
} catch {
    Write-Log "auto-reparo falhou: $($_.Exception.Message)" 'WARN'
}

Write-Log 'aguardando CS2'

# ---- loop principal --------------------------------------------------
try {
    while ($true) {

        # espera o CS2 aparecer. Poll leve, e SO fora da partida.
        $proc = $null
        while (-not $proc) {
            $proc = Get-Process -Name $GameProcess -ErrorAction SilentlyContinue |
                    Select-Object -First 1
            if (-not $proc) { Start-Sleep -Seconds 2 }
        }

        $cfg = Get-Config

        # espera a janela existir: evita disputar a troca de modo
        # com a propria inicializacao do jogo
        $deadline = (Get-Date).AddSeconds(40)
        while ((Get-Date) -lt $deadline) {
            try {
                $proc.Refresh()
                if ($proc.HasExited) { break }
                if ($proc.MainWindowHandle -ne [IntPtr]::Zero) { break }
            } catch { break }
            Start-Sleep -Milliseconds 500
        }

        if ($proc.HasExited) {
            Write-Log 'CS2 saiu antes de abrir janela, ignorando'
            continue
        }

        Write-Log ("jogo -> {0}x{1}@{2}" -f $cfg.resWidth, $cfg.resHeight, $cfg.resHz)
        Set-Resolution $cfg.monitor $cfg.resWidth $cfg.resHeight $cfg.resBPP $cfg.resHz

        # bloqueia sem consumir CPU ate o jogo fechar.
        # Durante a partida este processo nao acorda nenhuma vez.
        try { $proc.WaitForExit() } catch { }

        Restore-Desktop (Get-Config)
        Start-Sleep -Seconds 2
    }
}
finally {
    # se o script for morto com o jogo aberto, nao deixa o desktop em 4:3
    try {
        $cfg = Get-Config
        $cur = Get-CurrentMode $cfg.monitor
        if ($cur -and $cur.W -ne $cfg.defaultWidth) {
            Write-Log 'encerrando, restaurando desktop' 'WARN'
            Restore-Desktop $cfg
        }
    } catch { }
    if ($mutex) { try { $mutex.ReleaseMutex() } catch { } }
}
