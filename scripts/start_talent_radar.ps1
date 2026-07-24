[CmdletBinding()]
param(
    [int]$ApiPort = 8000,
    [int]$DashboardPort = 8501,
    [int]$CocCocDebugPort = 9223
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
$coccocUserData = Join-Path $env:LOCALAPPDATA "CocCoc\Browser\User Data"
$coccocControlUserData = Join-Path $projectRoot "data\coccoc_huy_user_data"
$debugEndpoint = "http://127.0.0.1:$CocCocDebugPort/json/version"

if (-not (Test-Path -LiteralPath $coccocControlUserData)) {
    New-Item `
        -ItemType Junction `
        -Path $coccocControlUserData `
        -Target $coccocUserData | Out-Null
}

Start-Sleep -Seconds 2

$controlledCocCoc = $false
try {
    $response = Invoke-WebRequest -Uri $debugEndpoint -UseBasicParsing -TimeoutSec 1
    $controlledCocCoc = $response.StatusCode -eq 200
} catch {
    $controlledCocCoc = $false
}

if ($controlledCocCoc) {
    Start-Process `
        -FilePath $coccocExecutable `
        -ArgumentList @("--profile-directory=Default", $dashboardUrl)
} elseif (Get-Process browser -ErrorAction SilentlyContinue) {
    Write-Warning (
        "Coc Coc is already running without Talent Radar control. Close Coc Coc once " +
        "and run this launcher again."
    )
} else {
    Start-Process `
        -FilePath $coccocExecutable `
        -ArgumentList @(
            "`"--user-data-dir=$coccocControlUserData`"",
            "--profile-directory=Default",
            "--remote-debugging-port=$CocCocDebugPort",
            "--remote-debugging-address=127.0.0.1",
            "--no-first-run",
            "--no-default-browser-check",
            $dashboardUrl
        )
}

Write-Output "Talent Radar: $dashboardUrl"
