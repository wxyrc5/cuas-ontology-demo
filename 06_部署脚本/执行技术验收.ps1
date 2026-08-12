$ErrorActionPreference = 'Stop'

$packageRoot = Split-Path -Parent $PSScriptRoot
$workspaceRoot = Split-Path -Parent $packageRoot
$pythonPath = Join-Path $workspaceRoot '.venv-cuas\python.exe'
$notebookRunner = Join-Path $PSScriptRoot 'run_notebooks.py'
$appVerifier = Join-Path $PSScriptRoot 'verify_streamlit_app.py'
$metricExporter = Join-Path $PSScriptRoot 'export_current_metrics.py'
$traceExporter = Join-Path $PSScriptRoot 'export_20_uav_trace.py'
$finalAuditor = Join-Path $PSScriptRoot 'validate_final_state.py'
$deploySync = Join-Path $PSScriptRoot 'sync_streamlit_deploy.ps1'
$liveSmoke = Join-Path $PSScriptRoot 'smoke_test_streamlit.ps1'
$releaseManifest = Join-Path $PSScriptRoot 'generate_release_manifest.py'

if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "Local Python environment not found: $pythonPath"
}

$requiredScripts = @($notebookRunner, $appVerifier, $metricExporter, $traceExporter, $finalAuditor, $deploySync, $liveSmoke, $releaseManifest)
$missingScripts = $requiredScripts | Where-Object { -not (Test-Path -LiteralPath $_ -PathType Leaf) }
if ($missingScripts) {
    throw "Required acceptance scripts are missing: $($missingScripts -join ', ')"
}

function Invoke-CheckedPython {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath,
        [Parameter(Mandatory = $true)]
        [string]$StepName
    )
    Write-Host "`n[$StepName]" -ForegroundColor Cyan
    & $pythonPath $ScriptPath
    if ($LASTEXITCODE -ne 0) {
        throw "$StepName failed with exit code $LASTEXITCODE"
    }
}

Push-Location $packageRoot
try {
    Invoke-CheckedPython -ScriptPath $notebookRunner -StepName '1/11 Execute all four notebooks'
    Invoke-CheckedPython -ScriptPath $traceExporter -StepName '2/11 Export 20-target synthetic event ledger'
    Invoke-CheckedPython -ScriptPath $metricExporter -StepName '3/11 Export preliminary metric snapshot'
    Invoke-CheckedPython -ScriptPath $appVerifier -StepName '4/11 Verify Streamlit pages and assets'
    Invoke-CheckedPython -ScriptPath $metricExporter -StepName '5/11 Export verified metric snapshot'
    Invoke-CheckedPython -ScriptPath $appVerifier -StepName '6/11 Re-verify pages against current metrics'
    Invoke-CheckedPython -ScriptPath $metricExporter -StepName '7/11 Lock the re-verified acceptance summary'
    Write-Host "`n[8/11 Synchronize deployable Streamlit mirror]" -ForegroundColor Cyan
    & $deploySync
    Write-Host "`n[9/11 Launch isolated live Streamlit smoke test]" -ForegroundColor Cyan
    & $liveSmoke
    Invoke-CheckedPython -ScriptPath $finalAuditor -StepName '10/11 Cross-file hash and metric audit'
    Invoke-CheckedPython -ScriptPath $releaseManifest -StepName '11/11 Generate authoritative release manifest'
} finally {
    Pop-Location
}

Write-Host "`nTechnical acceptance passed." -ForegroundColor Green
