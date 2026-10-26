# Felo Listener installer for Daniel's work PC (Windows). Run in PowerShell from this folder:
#   powershell -ExecutionPolicy Bypass -File .\install.ps1
# It: checks Python (installs Python 3.12 with winget if missing), creates a private environment in
# %LOCALAPPDATA%\FeloListener, installs the listener's packages, copies the program and the "Hey Felo" model,
# and makes it start by itself (hidden) every time you log in to Windows. Nothing else on the PC is changed.
$ErrorActionPreference = "Stop"
$Home2 = Join-Path $env:LOCALAPPDATA "FeloListener"
$Src = Split-Path -Parent $MyInvocation.MyCommand.Path
New-Item -ItemType Directory -Force -Path $Home2 | Out-Null

function Find-Python {
  foreach ($c in @("py -3.12", "py -3.11", "python")) {
    try { $v = & cmd /c "$c --version 2>&1"; if ($v -match "Python 3\.(1[0-2])") { return $c } } catch {}
  }
  return $null
}
$py = Find-Python
if (-not $py) {
  Write-Host "Installing Python 3.12 (winget)..."
  winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements | Out-Null
  $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
  $py = Find-Python
  if (-not $py) { throw "Python could not be installed. Install Python 3.12 from python.org and run this again." }
}
Write-Host "Using $py"
& cmd /c "$py -m venv `"$Home2\venv`""
& "$Home2\venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
& "$Home2\venv\Scripts\python.exe" -m pip install --quiet -r (Join-Path $Src "requirements.txt")
Copy-Item (Join-Path $Src "felo_listener.py"), (Join-Path $Src "hey_felo.onnx"), (Join-Path $Src "melspectrogram.onnx"), (Join-Path $Src "embedding_model.onnx") $Home2 -Force

# start hidden at every Windows log-in
$action = New-ScheduledTaskAction -Execute "$Home2\venv\Scripts\pythonw.exe" -Argument "`"$Home2\felo_listener.py`"" -WorkingDirectory $Home2
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 3650)
Register-ScheduledTask -TaskName "Felo Listener" -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName "Felo Listener"
Write-Host ""
Write-Host "Felo Listener is installed and running. Say 'Hey Felo'."
Write-Host "Log: $Home2\felo-listener.log"
Write-Host "Stop it:   Stop-ScheduledTask -TaskName 'Felo Listener'"
Write-Host "Remove it: Unregister-ScheduledTask -TaskName 'Felo Listener' -Confirm:`$false"
