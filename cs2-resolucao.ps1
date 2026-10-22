# ============================================================
#  cs2-resolucao.ps1  (v2)
#
#  Troca a resolucao do desktop quando o CS2 abre e restaura
#  quando fecha, para que o alt-tab nao force troca de modo
#  de video.
#
#  Opcionalmente troca tambem o digital vibrance (NVIDIA), no
#  mesmo monitor do config. Desligado por padrao: so age se o
#  cs2-config.json trouxer "vibranceEnabled": true.
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

# Set-StrictMode reclama de variavel nao definida, entao ja nascem declaradas
$script:VibranceReady = $false
$script:VibranceWarned = $false

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

# Os campos de vibrance sao opcionais de proposito: um cs2-config.json
# gravado por uma versao anterior do app nao tem nenhum deles, e o daemon
# precisa continuar funcionando com esse arquivo sem reclamar.
function Get-CfgValue {
    param($Cfg, [string]$Name, $Default)
    if (-not $Cfg.PSObject.Properties.Name.Contains($Name)) { return $Default }
    $value = $Cfg.$Name
    if ($null -eq $value) { return $Default }
    return $value
}

function Get-CfgInt {
    param($Cfg, [string]$Name, [int]$Default)
    $value = Get-CfgValue $Cfg $Name $Default
    try { return [int]$value } catch { return $Default }
}

function Get-CfgBool {
    param($Cfg, [string]$Name, [bool]$Default)
    $value = Get-CfgValue $Cfg $Name $Default
    try { return [bool]$value } catch { return $Default }
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

# ---- digital vibrance (NVAPI) ---------------------------------------
# A NVAPI nao exporta as funcoes por nome: exporta um unico
# nvapi_QueryInterface(id) que devolve o ponteiro de cada uma. Os ids sao
# valores internos, conhecidos por engenharia reversa e estaveis ha muitos
# anos, mas sem garantia da NVIDIA. Por isso tudo aqui e opcional: se
# qualquer passo falhar, o daemon segue trocando resolucao normalmente.
#
# Usa a variante Ex (escala 0-100, padrao 50), que e a mesma do slider do
# Painel de Controle da NVIDIA. A GetDVCInfo antiga e 0-63 com 0 = sem
# boost, o que daria um numero que nao bate com o que se ve no painel.
#
# So mexe no monitor configurado: casa o handle da NVAPI com o nome de
# device (\\.\DISPLAYn) por NvAPI_GetAssociatedNvidiaDisplayName.
Add-Type @'
using System;
using System.Text;
using System.Runtime.InteropServices;

public static class CS2Nv {
  [DllImport("kernel32", CharSet=CharSet.Ansi)] static extern IntPtr LoadLibrary(string n);
  [DllImport("kernel32", CharSet=CharSet.Ansi)] static extern IntPtr GetProcAddress(IntPtr m, string n);

  [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate IntPtr DQuery(uint id);
  [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate int DSimple();
  [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate int DEnum(int i, ref IntPtr h);
  [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate int DName(IntPtr d, StringBuilder s);
  [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate int DGet(IntPtr d, uint o, ref DVCEX i);
  [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate int DSet(IntPtr d, uint o, ref DVCEX i);

  [StructLayout(LayoutKind.Sequential)]
  public struct DVCEX { public uint version; public int current, min, max, def; }

  const uint ID_INIT = 0x0150E828, ID_UNLOAD = 0xD22BDD7E, ID_ENUM = 0x9ABDD40D,
             ID_NAME = 0x22A78B05, ID_GETEX = 0x0E45002D, ID_SETEX = 0x4A82C2B1;

  static uint Ver { get { return (uint)(20 | (1 << 16)); } }

  static DQuery _q; static DSimple _init, _unload; static DEnum _enum;
  static DName _name; static DGet _get; static DSet _set;
  static bool _ready;

  static T Fn<T>(uint id) where T : class {
    IntPtr p = _q(id);
    if (p == IntPtr.Zero) return null;
    return Marshal.GetDelegateForFunctionPointer(p, typeof(T)) as T;
  }

  public static bool Init() {
    if (_ready) return true;
    try {
      IntPtr mod = LoadLibrary("nvapi64.dll");
      if (mod == IntPtr.Zero) return false;
      IntPtr q = GetProcAddress(mod, "nvapi_QueryInterface");
      if (q == IntPtr.Zero) return false;
      _q = (DQuery)Marshal.GetDelegateForFunctionPointer(q, typeof(DQuery));
      _init = Fn<DSimple>(ID_INIT); _unload = Fn<DSimple>(ID_UNLOAD);
      _enum = Fn<DEnum>(ID_ENUM);   _name  = Fn<DName>(ID_NAME);
      _get  = Fn<DGet>(ID_GETEX);   _set   = Fn<DSet>(ID_SETEX);
      if (_init == null || _enum == null || _name == null || _get == null || _set == null)
        return false;
      if (_init() != 0) return false;
      _ready = true;
      return true;
    } catch { return false; }
  }

  public static void Shutdown() {
    try { if (_ready && _unload != null) _unload(); } catch { }
    _ready = false;
  }

  // O handle e reenumerado a cada chamada de proposito: depois de uma troca
  // de modo ou de um hotplug o handle antigo pode nao valer mais.
  static IntPtr Handle(string device) {
    for (int i = 0; i < 16; i++) {
      IntPtr h = IntPtr.Zero;
      if (_enum(i, ref h) != 0) break;
      StringBuilder sb = new StringBuilder(64);
      if (_name(h, sb) != 0) continue;
      if (string.Equals(sb.ToString(), device, StringComparison.OrdinalIgnoreCase))
        return h;
    }
    return IntPtr.Zero;
  }

  // -1 = indisponivel
  public static int GetLevel(string device) {
    if (!_ready) return -1;
    try {
      IntPtr h = Handle(device);
      if (h == IntPtr.Zero) return -1;
      DVCEX info = new DVCEX(); info.version = Ver;
      if (_get(h, 0, ref info) != 0) return -1;
      return info.current;
    } catch { return -1; }
  }

  // devolve o nivel aplicado, ou -1
  public static int SetLevel(string device, int level) {
    if (!_ready) return -1;
    try {
      IntPtr h = Handle(device);
      if (h == IntPtr.Zero) return -1;
      DVCEX info = new DVCEX(); info.version = Ver;
      if (_get(h, 0, ref info) != 0) return -1;
      if (level < info.min) level = info.min;
      if (level > info.max) level = info.max;
      DVCEX w = new DVCEX(); w.version = Ver; w.current = level;
      if (_set(h, 0, ref w) != 0) return -1;
      return level;
    } catch { return -1; }
  }
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
    if (-not $actual) {
        # sem leitura nao da para confirmar nada; registrar evita o caso em
        # que o modo nao aplicou e o log nao mostra absolutamente nada
        Write-Log "nao consegui ler o modo de $Monitor para conferir" 'WARN'
    } elseif ($actual.W -ne $W -or $actual.H -ne $H) {
        Write-Log "modo nao aplicou ($($actual.W)x$($actual.H)), tentando de novo" 'WARN'
        & $NirCmd setdisplay "monitor:$Monitor" $W $H $Bpp $Hz -updatereg
        Start-Sleep -Milliseconds 600
    }
}

# Aplica o vibrance SO no monitor do config, e so se o usuario ligou a
# opcao. Vai depois da troca de resolucao de proposito: uma mudanca de modo
# pode reiniciar o DVC, e nessa ordem nao importa se reinicia.
function Set-Vibrance {
    param($Cfg, [string]$Field)

    if (-not (Get-CfgBool $Cfg 'vibranceEnabled' $false)) { return }

    $level = Get-CfgInt $Cfg $Field -1
    if ($level -lt 0) { return }

    # Carga tardia da NVAPI. O daemon sobe uma vez e fica semanas no ar; se a
    # inicializacao so acontecesse no pre-voo, ligar o vibrance no app com o
    # daemon ja rodando nao teria efeito nenhum ate reiniciar o script, o que
    # contraria a regra do projeto de que mudanca no app vale no proximo jogo.
    if (-not $script:VibranceReady) {
        $script:VibranceReady = [CS2Nv]::Init()
        if ($script:VibranceReady) {
            Write-Log 'NVAPI carregada sob demanda'
        } else {
            if (-not $script:VibranceWarned) {
                Write-Log 'vibrance ligado no config, mas a NVAPI nao respondeu' 'WARN'
                $script:VibranceWarned = $true
            }
            return
        }
    }

    $device = Resolve-Device $Cfg.monitor
    $applied = [CS2Nv]::SetLevel($device, $level)
    if ($applied -lt 0) {
        Write-Log "vibrance nao aplicou em $device (alvo $level)" 'WARN'
    } else {
        Write-Log ("vibrance {0} -> {1}" -f $device, $applied)
    }
}

function Restore-Desktop {
    param($Cfg)
    Write-Log ("desktop -> {0}x{1}@{2}" -f $Cfg.defaultWidth, $Cfg.defaultHeight, $Cfg.defaultHz)
    Set-Resolution $Cfg.monitor $Cfg.defaultWidth $Cfg.defaultHeight $Cfg.resBPP $Cfg.defaultHz
    Set-Vibrance $Cfg 'vibranceDesktop'
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

    # o driver guarda o DVC entre sessoes, entao se a maquina caiu no meio da
    # partida o nivel de jogo pode ter sobrevivido ao boot. Set-Vibrance ja
    # checa se esta ligado e carrega a NVAPI por conta propria.
    Set-Vibrance $cfg 'vibranceDesktop'
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
        Set-Vibrance $cfg 'vibranceGame'

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
        } else {
            # resolucao ja estava certa, mas o vibrance pode estar no de jogo
            Set-Vibrance $cfg 'vibranceDesktop'
        }
    } catch { }
    try { [CS2Nv]::Shutdown() } catch { }
    if ($mutex) { try { $mutex.ReleaseMutex() } catch { } }
}
