param(
    [int]$PreferredPort = 8510,
    [int]$TimeoutSeconds = 30
)

$ErrorActionPreference = 'Stop'

$packageRoot = Split-Path -Parent $PSScriptRoot
$workspaceRoot = Split-Path -Parent $packageRoot
$pythonPath = Join-Path $workspaceRoot '.venv-cuas\python.exe'
$appDir = Join-Path $packageRoot '03_源码\streamlit_app'
$appPath = Join-Path $appDir 'app.py'
$validationDir = Join-Path $packageRoot '05_Notebook与数据\验证输出'
$reportPath = Join-Path $validationDir 'live_streamlit_smoke.json'
$logDir = Join-Path $packageRoot '.runlogs\live_smoke'

if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "Local Python environment not found: $pythonPath"
}
if (-not (Test-Path -LiteralPath $appPath -PathType Leaf)) {
    throw "Streamlit entry not found: $appPath"
}

New-Item -ItemType Directory -Path $validationDir -Force | Out-Null
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

$port = $PreferredPort
while (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
    $port++
}
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$stdoutLog = Join-Path $logDir ("streamlit_{0}_{1}_stdout.log" -f $timestamp, $port)
$stderrLog = Join-Path $logDir ("streamlit_{0}_{1}_stderr.log" -f $timestamp, $port)
$arguments = @(
    '-m', 'streamlit', 'run', 'app.py',
    '--server.headless=true',
    ("--server.port={0}" -f $port),
    '--server.address=127.0.0.1',
    '--browser.gatherUsageStats=false'
)

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$process = Start-Process -FilePath $pythonPath -ArgumentList $arguments `
    -WorkingDirectory $appDir -WindowStyle Hidden `
    -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog -PassThru
$health = $null
$root = $null
$passed = $false
$exitedEarly = $false

try {
    for ($attempt = 0; $attempt -lt $TimeoutSeconds; $attempt++) {
        $process.Refresh()
        if ($process.HasExited) {
            $exitedEarly = $true
            break
        }
        try {
            $health = Invoke-WebRequest `
                -Uri ("http://127.0.0.1:{0}/_stcore/health" -f $port) `
                -UseBasicParsing -TimeoutSec 2
            $root = Invoke-WebRequest `
                -Uri ("http://127.0.0.1:{0}/" -f $port) `
                -UseBasicParsing -TimeoutSec 2
            if (
                $health.StatusCode -eq 200 -and
                $health.Content.Trim() -eq 'ok' -and
                $root.StatusCode -eq 200 -and
                $root.Content -match 'Streamlit'
            ) {
                $passed = $true
                break
            }
        } catch {
            # The server may still be starting; retry until TimeoutSeconds.
        }
        Start-Sleep -Seconds 1
    }
} finally {
    $stopwatch.Stop()
    $process.Refresh()
    if (-not $process.HasExited) {
        Stop-Process -Id $process.Id -ErrorAction SilentlyContinue
    }
    Start-Sleep -Milliseconds 300
}

$processStillRunning = [bool](Get-Process -Id $process.Id -ErrorAction SilentlyContinue)
$stderrText = if (Test-Path -LiteralPath $stderrLog) {
    Get-Content -LiteralPath $stderrLog -Raw
} else {
    ''
}
$report = [ordered]@{
    schema_version = 1
    generated_at = (Get-Date).ToString('o')
    status = if ($passed -and -not $processStillRunning) { 'passed' } else { 'failed' }
    app = '03_源码/streamlit_app/app.py'
    preferred_port = $PreferredPort
    tested_port = $port
    startup_seconds = [math]::Round($stopwatch.Elapsed.TotalSeconds, 3)
    health_status = if ($health) { $health.StatusCode } else { $null }
    health_body = if ($health) { $health.Content.Trim() } else { $null }
    root_status = if ($root) { $root.StatusCode } else { $null }
    root_contains_streamlit = if ($root) { [bool]($root.Content -match 'Streamlit') } else { $false }
    process_exited_early = $exitedEarly
    process_still_running_after_cleanup = $processStillRunning
    stderr_contains_traceback = [bool]($stderrText -match 'Traceback')
    logs = [ordered]@{
        stdout = $stdoutLog
        stderr = $stderrLog
        excluded_from_release = $true
    }
}
$report | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $reportPath -Encoding utf8
$report | ConvertTo-Json -Depth 4
Write-Host "Smoke report: $reportPath"

if ($report.status -ne 'passed') {
    throw "Streamlit live smoke test failed; see $reportPath"
}
