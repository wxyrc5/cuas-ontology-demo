param(
    [switch]$ForceReinstall
)

$ErrorActionPreference = 'Stop'
$packageRoot = Split-Path -Parent $PSScriptRoot
$workspaceRoot = Split-Path -Parent $packageRoot
$environmentPath = Join-Path $workspaceRoot '.venv-cuas'
$pythonPath = Join-Path $environmentPath 'python.exe'
$requirementsPath = Join-Path $PSScriptRoot 'requirements-local.txt'

if ((Test-Path -LiteralPath $pythonPath -PathType Leaf) -and -not $ForceReinstall) {
    Write-Host "本地环境已存在：$environmentPath" -ForegroundColor Green
    & $pythonPath --version
    exit 0
}

$condaCommand = Get-Command conda -ErrorAction SilentlyContinue
if ($null -eq $condaCommand -and $env:CONDA_EXE) {
    $condaExecutable = $env:CONDA_EXE
} elseif ($null -ne $condaCommand) {
    $condaExecutable = $condaCommand.Source
} else {
    throw '未找到 Conda。请先安装 Miniconda/Anaconda，或把 CONDA_EXE 指向 conda.exe。'
}

if ($ForceReinstall -and (Test-Path -LiteralPath $environmentPath)) {
    throw "为防止误删，脚本不会自动覆盖现有环境。请先手动移走：$environmentPath"
}

Write-Host '正在创建 Python 3.11 隔离环境……' -ForegroundColor Cyan
& $condaExecutable create --prefix $environmentPath 'python=3.11' pip --yes
if ($LASTEXITCODE -ne 0) {
    throw 'Conda 环境创建失败。'
}

Write-Host '正在安装本项目已验证依赖……' -ForegroundColor Cyan
& $pythonPath -m pip install --requirement $requirementsPath
if ($LASTEXITCODE -ne 0) {
    throw 'Python 依赖安装失败。'
}

& $pythonPath -m pip check
if ($LASTEXITCODE -ne 0) {
    throw '依赖一致性检查失败。'
}
Write-Host "环境安装完成：$environmentPath" -ForegroundColor Green
