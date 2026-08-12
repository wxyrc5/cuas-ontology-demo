param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 8501
)

$ErrorActionPreference = 'Stop'
$packageRoot = Split-Path -Parent $PSScriptRoot
$workspaceRoot = Split-Path -Parent $packageRoot
$appRoot = Join-Path $packageRoot '03_源码\streamlit_app'
$appEntry = Join-Path $appRoot 'app.py'
$pythonPath = Join-Path $workspaceRoot '.venv-cuas\python.exe'

if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "未找到隔离环境。请先运行：$PSScriptRoot\安装本地环境.ps1"
}
if (-not (Test-Path -LiteralPath $appEntry -PathType Leaf)) {
    throw "未找到 Streamlit 主入口：$appEntry"
}

& $pythonPath -c "import streamlit, plotly, rdflib, numpy, pandas; print('环境检查通过')"
if ($LASTEXITCODE -ne 0) {
    throw '运行依赖检查失败，请重新执行安装本地环境.ps1。'
}

Write-Host "项目地址：http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host '按 Ctrl+C 停止服务。' -ForegroundColor DarkGray
Push-Location $appRoot
try {
    & $pythonPath -m streamlit run $appEntry --server.port $Port --server.headless true --browser.gatherUsageStats false
} finally {
    Pop-Location
}
