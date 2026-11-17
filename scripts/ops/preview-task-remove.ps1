# Removes the scheduled tasks created by preview-task-install.ps1 (does not stop a running preview; use preview-stop.ps1).
foreach ($n in "PreClass Preview", "PreClass Preview Health") {
  if (Get-ScheduledTask -TaskName $n -ErrorAction SilentlyContinue) { Unregister-ScheduledTask -TaskName $n -Confirm:$false; Write-Host "removed $n" }
}
