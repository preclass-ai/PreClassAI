# Registers two user-scope scheduled tasks (no Admin): "PreClass Preview" (at logon, 3 retries 1 min apart)
# and "PreClass Preview Health" (every 10 min). Remove both with preview-task-remove.ps1.
$ErrorActionPreference = "Stop"
$ops = $PSScriptRoot
$me = "$env:USERDOMAIN\$env:USERNAME"
$ps = "powershell.exe"
function Arg($f) { "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ops\$f`"" }
$set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
  -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
$prin = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName "PreClass Preview" -Force -Description "At logon: waits for Docker, then runs scripts/ops/preview.ps1." -Settings $set -Principal $prin `
  -Action (New-ScheduledTaskAction -Execute $ps -Argument (Arg "preview-start.ps1")) `
  -Trigger (New-ScheduledTaskTrigger -AtLogOn -User $me) | Out-Null

$every10 = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(10) -RepetitionInterval (New-TimeSpan -Minutes 10)
Register-ScheduledTask -TaskName "PreClass Preview Health" -Force -Description "Every 10 min: checks API, Caddy and tunnel; restarts what is down and writes the new URL to .agents/PREVIEW_URL.md. Does not commit or push." -Settings $set -Principal $prin `
  -Action (New-ScheduledTaskAction -Execute $ps -Argument (Arg "preview-health.ps1")) -Trigger $every10 | Out-Null

Get-ScheduledTask -TaskName "PreClass Preview*" | Select-Object TaskName, State | Format-Table -AutoSize
