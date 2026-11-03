#Requires -Version 5.1
<#
.SYNOPSIS
Start or reuse this repository's local ReplayLab demo without exposing secrets.
.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts\start_demo.ps1
.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts\start_demo.ps1 -ProjectId <id> -NoBrowser
.NOTES
Does not install dependencies, change providers, approve proposals, or stop existing
processes. Logs and process ownership records stay in the ignored .artifacts folder.
#>
[CmdletBinding()]
param(
    [ValidatePattern('^[a-f0-9]{32}$')]
    [string]$ProjectId,
    [switch]$NoBrowser,
    [switch]$CheckOnly,
    [ValidateRange(10, 600)]
    [int]$WaitSeconds = 180
)

$ErrorActionPreference = 'Stop'
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$apiBase = 'http://127.0.0.1:8010'
$webBase = 'http://127.0.0.1:5173'
$expectedModel = 'meta-llama/Llama-3.2-3B-Instruct'
$pythonPath = Join-Path $repoRoot '.venv\Scripts\python.exe'
$artifactRoot = Join-Path $repoRoot '.artifacts'
$ownershipPath = Join-Path $artifactRoot 'demo-launcher-ownership.json'

function Get-Json([string]$Uri) {
    try {
        return Invoke-RestMethod -Uri $Uri -Method Get -TimeoutSec 3
    } catch {
        return $null
    }
}

function Test-WebReady {
    try {
        $response = Invoke-WebRequest -Uri $webBase -UseBasicParsing -TimeoutSec 3
        return $response.StatusCode -eq 200 -and $response.Content.Contains('<div id="root">')
    } catch {
        return $false
    }
}

function Get-Listeners {
    return @(Get-NetTCPConnection -State Listen -LocalPort 5173, 8010 -ErrorAction SilentlyContinue)
}

try {
    Write-Host 'ReplayLab demo: checking local dependencies and server configuration...'
    if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
        throw 'Project Python environment is missing. Run npm run setup before the demo.'
    }
    $nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
    if (-not $nodeCommand) { throw 'Node.js is missing. Install the version required by package.json.' }
    $nodeVersion = & $nodeCommand.Source --version
    if ($LASTEXITCODE -ne 0 -or [version]$nodeVersion.TrimStart('v') -lt [version]'22.12.0') {
        throw 'Node.js 22.12.0 or newer is required.'
    }
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot 'apps\web\node_modules\vite\bin\vite.js') -PathType Leaf)) {
        throw 'Frontend dependencies are missing. Run npm run setup before the demo.'
    }

    # All subprocess output is captured. Configuration failures can include input
    # values in third-party exceptions, so only our fixed safe message is shown.
    $configurationCode = @'
import json
import sys
from pathlib import Path
try:
    import cv2
    import httpx
    import rapidocr
    import uvicorn
    from app.core.config import Settings
    settings = Settings()
    models = Path(rapidocr.__file__).parent / "models"
    required = ["PP-OCRv6_det_small.onnx", "ch_ppocr_mobile_v2.0_cls_mobile.onnx", "PP-OCRv6_rec_small.onnx"]
    if not all((models / name).is_file() for name in required):
        raise ValueError("missing local OCR models")
    if settings.ai_provider != "local_meta":
        raise ValueError("local Meta must be configured explicitly")
    if settings.local_meta_base_url != "http://127.0.0.1:8083/v1":
        raise ValueError("the demo launcher expects the pinned loopback server")
    if settings.local_meta_model != "meta-llama/Llama-3.2-3B-Instruct":
        raise ValueError("the demo launcher expects the pinned Meta model")
    print(json.dumps({"valid": True, "mode": "local_meta", "uses_cloud_credentials": False}))
except Exception:
    sys.exit(1)
'@
    Push-Location (Join-Path $repoRoot 'apps\api')
    try {
        $safeConfiguration = $configurationCode | & $pythonPath - 2>&1
        $configurationExit = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    if ($configurationExit -ne 0) {
        throw 'Backend dependencies, local OCR files, or local Meta settings are invalid. Run npm run setup and scripts/setup-local-meta.py --activate. Configuration values were hidden.'
    }
    try { $configuration = ($safeConfiguration | Out-String) | ConvertFrom-Json } catch { $configuration = $null }
    if (-not $configuration -or -not $configuration.valid) {
        throw 'Backend configuration check returned an unexpected result. Configuration values were hidden.'
    }
    Write-Host 'Dependencies and local Meta settings: valid. No cloud API key is required by this mode.'

    $health = Get-Json ($apiBase + '/api/health')
    $webReady = Test-WebReady
    if (-not $health -or $health.status -ne 'ok' -or -not $webReady) {
        if ($CheckOnly) { throw 'The application is not running. Re-run this launcher without -CheckOnly.' }
        if ((Get-Listeners).Count -gt 0) {
            throw 'Only part of the app is healthy or a demo port is occupied. No process was stopped. Close the existing ReplayLab launcher, or inspect ports 5173 and 8010, then retry.'
        }
        New-Item -ItemType Directory -Path $artifactRoot -Force | Out-Null
        $devScript = Join-Path $repoRoot 'scripts\dev.mjs'
        $stdoutLog = Join-Path $artifactRoot 'demo-launcher.stdout.log'
        $stderrLog = Join-Path $artifactRoot 'demo-launcher.stderr.log'
        $child = Start-Process -FilePath $nodeCommand.Source -ArgumentList @('"' + $devScript + '"', '--demo') `
            -WorkingDirectory $repoRoot -WindowStyle Hidden -RedirectStandardOutput $stdoutLog `
            -RedirectStandardError $stderrLog -PassThru
        [ordered]@{
            root = $repoRoot; pid = $child.Id; executable = $nodeCommand.Source; script = $devScript
            started_at = [DateTime]::UtcNow.ToString('o'); state = 'started'; credentials_logged = $false; mode = 'demo'
        } | ConvertTo-Json | Set-Content -LiteralPath $ownershipPath -Encoding UTF8
        Write-Host ('Started this repository''s hidden demo launcher without backend file watching (PID ' + $child.Id + ').')
    } else {
        Write-Host 'Reusing the healthy frontend and backend. Existing processes remain running.'
    }

    $deadline = [DateTime]::UtcNow.AddSeconds($WaitSeconds)
    $modelReady = $false
    do {
        $health = Get-Json ($apiBase + '/api/health')
        $webReady = Test-WebReady
        $modelHealth = Get-Json 'http://127.0.0.1:8083/health'
        $modelList = Get-Json 'http://127.0.0.1:8083/v1/models'
        $modelReady = $modelHealth -and $modelHealth.status -eq 'ok' -and $modelList -and `
            @($modelList.data | Where-Object { $_.id -eq $expectedModel }).Count -gt 0
        if ($health -and $health.status -eq 'ok' -and $webReady -and $modelReady) { break }
        if ($CheckOnly) { break }
        Start-Sleep -Seconds 2
    } while ([DateTime]::UtcNow -lt $deadline)
    if (-not $health -or $health.status -ne 'ok' -or -not $webReady -or -not $modelReady) {
        throw 'The frontend, backend, or exact local Meta model did not become healthy. Check the ignored .artifacts/demo-launcher logs. No unrelated process was stopped.'
    }
    if ($health.provider.mode -ne 'local_meta' -or $health.provider.model -ne $expectedModel) {
        throw 'The running API has a different active provider. Select Local Meta Llama in ReplayLab settings, then rerun the launcher.'
    }

    if ($ProjectId) {
        $project = Get-Json ($apiBase + '/api/projects/' + $ProjectId)
    } else {
        $allProjects = Get-Json ($apiBase + '/api/projects')
        $project = @($allProjects | Where-Object {
            $_.name -like 'Hackathon live demonstration*' -and $_.status -eq 'ready' -and
            $_.task -and $_.task.modality -eq 'digital' -and $_.task.provider_mode -eq 'local_meta'
        } | Sort-Object created_at -Descending | Select-Object -First 1)[0]
    }
    if (-not $project -or $project.status -ne 'ready' -or -not $project.task -or
        $project.task.modality -ne 'digital' -or $project.task.provider_mode -ne 'local_meta' -or
        @($project.task.steps).Count -eq 0 -or $project.task.provenance.model -ne $expectedModel -or
        -not $project.task.provenance.request_id -or $project.task.provenance.local_only -ne $true -or
        $project.task.provenance.vision_inference -ne $false) {
        throw 'A ready, genuinely generated local Meta digital workflow was not found. Prepare the workflow as described in docs/DEMO_SETUP.md, or pass its identifier using -ProjectId. No project was changed.'
    }

    $approvedText = if ($project.approved) { 'approved' } else { 'awaiting review and approval' }
    Write-Host ('Prepared digital workflow: ' + $project.id + ' (' + @($project.task.steps).Count + ' steps; ' + $approvedText + ').')
    Write-Host ('Provider: local Meta Llama 3.2 3B. Exact model server is healthy: ' + $expectedModel)
    if ($health.provider.live_verified) {
        Write-Host 'API session: an actual local Meta inference response has been validated.'
    } else {
        Write-Host 'API session: inference has not yet been validated in this new server session. The prepared task records earlier genuine inference; the next live check will validate the current session.'
    }
    if (-not (Get-Command ffmpeg.exe -ErrorAction SilentlyContinue) -or
        -not (Get-Command ffprobe.exe -ErrorAction SilentlyContinue)) {
        Write-Host 'Recording note: FFmpeg/FFprobe are unavailable; the app is ready, but MP4 capture/validation needs those tools or OBS.'
    }
    Write-Host 'READY: frontend, backend, local Meta model, and prepared workflow are available.' -ForegroundColor Green
    Write-Host ('Open ' + $webBase + ', choose the prepared project, and review its steps before approving guided practice.')
    if (-not $NoBrowser) { Start-Process $webBase | Out-Null }
    exit 0
} catch {
    [Console]::Error.WriteLine('Demo preparation stopped: ' + $_.Exception.Message)
    exit 1
}
