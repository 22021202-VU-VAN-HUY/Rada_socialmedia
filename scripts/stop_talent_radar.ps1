[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = (Split-Path -Parent $PSScriptRoot)
$runtimeDirectory = (Join-Path $projectRoot "data\runtime")

$pidPath = Join-Path $runtimeDirectory "api.pid"
if (-not (Test-Path -LiteralPath $pidPath)) {
    return
}

$processId = [int](Get-Content -Raw -LiteralPath $pidPath)
$process = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
if ($process) {
    $commandLine = [string]$process.CommandLine
    if (-not $commandLine.Contains("talent_radar.api.main")) {
        throw "PID $processId does not look like a Talent Radar process. Refusing to stop it."
    }
    Stop-Process -Id $processId
    Write-Output "Stopped api (PID $processId)."
}
Remove-Item -LiteralPath $pidPath -Force
