# Safe RAM cleanup. Default is DRY-RUN: prints a table only.
# Usage: .\clean_ram.ps1            -> list top processes, mark protected ones
#        .\clean_ram.ps1 -Ids 123,456 -> gracefully close exactly those Ids
# Never runs elevated, never wildcards, never kills by image name.
param([int[]]$Ids = @())

$protectedPrefixes = @(
  'System','Idle','Registry','smss','csrss','wininit','winlogon','services','lsass','svchost','dwm','explorer',
  'sihost','fontdrvhost','ctfmon','RuntimeBroker','SearchHost','StartMenuExperienceHost','ShellExperienceHost',
  'TextInputHost','ApplicationFrameHost','SecurityHealth','MsMpEng','NisSrv','audiodg','spoolsv','WUDFHost',
  'nvcontainer','NVDisplay','igfx','RtkAudUService','taskmgr',
  'claude','node','python','pythonw','uv','uvicorn','git','ssh','pwsh','powershell','cmd','conhost',
  'WindowsTerminal','OpenConsole','Code','Antigravity','language_server',
  'Docker Desktop','com.docker','vpnkit','vmmem','vmmemWSL','wsl','wslservice','wslhost','postgres',
  'unikey','EVKey','OneDrive','TeamViewer','AnyDesk'
)

# Ancestors of this session are never killable.
$ancestry = @(); $cur = $PID
while ($cur -and $cur -ne 0 -and $ancestry -notcontains $cur) {
  $ancestry += $cur
  $p = Get-CimInstance Win32_Process -Filter "ProcessId=$cur"
  if (-not $p) { break }
  $cur = $p.ParentProcessId
}

function Test-Protected($proc) {
  if ($ancestry -contains $proc.Id) { return $true }
  foreach ($n in $protectedPrefixes) { if ($proc.Name -like "$n*") { return $true } }
  return $false
}

if ($Ids.Count -eq 0) {
  Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 25 |
    Select-Object Name, Id, @{n='MB';e={[int]($_.WorkingSet64/1MB)}},
      @{n='Protected';e={Test-Protected $_}}, MainWindowTitle | Format-Table -AutoSize
  Write-Host "DRY-RUN. Pass -Ids <id,id> to close specific unprotected processes."
  return
}

foreach ($id in $Ids) {
  $proc = Get-Process -Id $id -ErrorAction SilentlyContinue
  if (-not $proc) { Write-Host "Id $id : not running"; continue }
  if (Test-Protected $proc) { Write-Host "Id $id ($($proc.Name)) : REFUSED (protected)"; continue }
  [void]$proc.CloseMainWindow()
  Start-Sleep -Seconds 3
  if (-not $proc.HasExited) { Stop-Process -Id $id }
  Write-Host "Id $id ($($proc.Name)) : closed"
}
