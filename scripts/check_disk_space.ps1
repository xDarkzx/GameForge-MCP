# Checks free space on the drive this repo lives on before the stable-audio-3
# clone + venv + checkpoint download. Same pattern as SongForge-MCP's own
# check_disk_space.ps1 (that project hit 100% disk usage once from exactly
# this kind of download landing on an already-tight drive).
param(
    [int]$RequiredGB = 15
)

$drive = (Get-Item $PSScriptRoot).PSDrive.Name
$freeGB = [math]::Round((Get-PSDrive $drive).Free / 1GB, 1)

Write-Host "Drive $($drive): $freeGB GB free (need ~$RequiredGB GB)"

if ($freeGB -lt $RequiredGB) {
    Write-Host "Not enough free space."
    exit 1
}
exit 0
