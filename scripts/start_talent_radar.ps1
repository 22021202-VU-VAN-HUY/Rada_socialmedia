[CmdletBinding()]
param(
    [int]$ApiPort = 8000,
    [int]$DashboardPort = 8501
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeDirectory = Join-Path $projectRoot "data\runtime"
$logDirectory = Join-Path $runtimeDirectory "logs"
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null

function Start-TalentRadarProcess {
    param(
        [string]$Name,
        [string[]]$Arguments
    )

    $pidPath = Join-Path $runtimeDirectory "$Name.pid"
    if (Test-Path -LiteralPath $pidPath) {
        $existingPid = [int](Get-Content -Raw -LiteralPath $pidPath)
        if (Get-Process -Id $existingPid -ErrorAction SilentlyContinue) {
            Write-Output "$Name is already running (PID $existingPid)."
            return
        }
    }

    $process = Start-Process `
        -FilePath "python" `
        -ArgumentList $Arguments `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logDirectory "$Name.out.log") `
        -RedirectStandardError (Join-Path $logDirectory "$Name.err.log") `
        -PassThru
    Set-Content -LiteralPath $pidPath -Value $process.Id -Encoding ascii
    Write-Output "Started $Name (PID $($process.Id))."
}

Start-TalentRadarProcess -Name "api" -Arguments @(
    "-m", "uvicorn", "talent_radar.api.main:app",
    "--host", "127.0.0.1",
    "--port", "$ApiPort"
)

Start-Sleep -Seconds 2

Start-TalentRadarProcess -Name "dashboard" -Arguments @(
    "-m", "streamlit", "run", "src/talent_radar/dashboard/app.py",
    "--server.address", "127.0.0.1",
    "--server.port", "$DashboardPort",
    "--server.headless", "true"
)

$dashboardUrl = "http://localhost:$DashboardPort"
$coccocExecutable = "C:\Program Files\CocCoc\Browser\Application\browser.exe"

Start-Sleep -Seconds 2

Start-Process `
    -FilePath $coccocExecutable `
    -ArgumentList @("--profile-directory=Default", $dashboardUrl)

Write-Output "Talent Radar: $dashboardUrl"
