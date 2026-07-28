[CmdletBinding()]
param(
    [int]$ApiPort = 8000
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$runtimeDirectory = Join-Path $projectRoot "data\runtime"
$logDirectory = Join-Path $runtimeDirectory "logs"
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null

function Start-TalentRadarDatabase {
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        $dockerDesktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        if (-not (Test-Path -LiteralPath $dockerDesktop)) {
            throw "Docker Desktop is required to run the PostgreSQL database."
        }
        Start-Process -FilePath $dockerDesktop -WindowStyle Hidden
        $ready = $false
        for ($attempt = 0; $attempt -lt 60; $attempt++) {
            Start-Sleep -Seconds 2
            docker info *> $null
            if ($LASTEXITCODE -eq 0) {
                $ready = $true
                break
            }
        }
        if (-not $ready) {
            throw "Docker Desktop did not become ready within two minutes."
        }
    }

    docker compose -f (Join-Path $projectRoot "docker-compose.yml") up -d db
    if ($LASTEXITCODE -ne 0) {
        throw "PostgreSQL could not be started."
    }

    $healthy = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        docker compose -f (Join-Path $projectRoot "docker-compose.yml") exec -T db `
            pg_isready -U talent_radar -d talent_radar *> $null
        if ($LASTEXITCODE -eq 0) {
            $healthy = $true
            break
        }
        Start-Sleep -Seconds 2
    }
    if (-not $healthy) {
        throw "PostgreSQL did not become healthy within one minute."
    }

    & python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        throw "Database migration failed."
    }
}

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

Start-TalentRadarDatabase

Start-TalentRadarProcess -Name "api" -Arguments @(
    "-m", "uvicorn", "talent_radar.api.main:app",
    "--host", "127.0.0.1",
    "--port", "$ApiPort"
)

Start-Sleep -Seconds 2

$appUrl = "http://127.0.0.1:$ApiPort"
Start-Process $appUrl

Write-Output "Talent Radar: $appUrl"
