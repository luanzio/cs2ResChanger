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
    Write-Output "$gameProcess detectado. Alterando resolução para $($cfg.resWidth)x$($cfg.resHeight)@$($cfg.resHz) (bpp $($cfg.resBPP))..."
    Set-Resolution $cfg.monitor $cfg.resWidth $cfg.resHeight $cfg.resBPP $cfg.resHz

    while (Get-Process -Name $gameProcess -ErrorAction SilentlyContinue) {
        Start-Sleep -Seconds 2
    }

    $cfg = Load-Config
    Write-Output "$gameProcess fechado. Restaurando para $($cfg.defaultWidth)x$($cfg.defaultHeight)@$($cfg.defaultHz) (bpp $($cfg.resBPP))..."
    Set-Resolution $cfg.monitor $cfg.defaultWidth $cfg.defaultHeight $cfg.resBPP $cfg.defaultHz

    Start-Sleep -Seconds 2
}
