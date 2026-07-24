[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = (Split-Path -Parent $PSScriptRoot)
$runtimeDirectory = (Join-Path $projectRoot "data\runtime")

foreach ($name in @("dashboard", "api")) {
    $pidPath = Join-Path $runtimeDirectory "$name.pid"
    if (-not (Test-Path -LiteralPath $pidPath)) {
        continue
    }

    $processId = [int](Get-Content -Raw -LiteralPath $pidPath)
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
    if ($process) {
        $commandLine = [string]$process.CommandLine
        $isTalentRadar = $commandLine.Contains("talent_radar") -or $commandLine.Contains("streamlit")
        if (-not $isTalentRadar) {
            throw "PID $processId does not look like a Talent Radar process. Refusing to stop it."
        }
        Stop-Process -Id $processId
        Write-Output "Stopped $name (PID $processId)."
    }
    Remove-Item -LiteralPath $pidPath -Force
}

