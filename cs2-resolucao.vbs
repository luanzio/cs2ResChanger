' ============================================================
'  cs2-resolucao.vbs
'
'  Inicia o cs2-resolucao.ps1 completamente oculto.
'
'  O terceiro argumento de objShell.Run e o estilo de janela:
'  0 = oculta. E por isso que o daemon nunca mostra console,
'  diferente de um .cmd chamado pelo Steam como %command%.
'
'  Instalacao:
'    1. Coloque este arquivo e o cs2-resolucao.ps1 em C:\nircmd\
'    2. Win+R -> shell:startup
'    3. Crie um atalho para este .vbs dentro da pasta aberta
'
'  Nao precisa de Admin.
' ============================================================

Dim objShell, scriptDir
Set objShell = CreateObject("WScript.Shell")
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

objShell.Run "powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File """ & scriptDir & "\cs2-resolucao.ps1""", 0, False
