$ErrorActionPreference = 'Stop'
$packageRoot = Split-Path -Parent $PSScriptRoot
$workspaceRoot = Split-Path -Parent $packageRoot
$pythonPath = Join-Path $workspaceRoot '.venv-cuas\python.exe'
$runner = Join-Path $PSScriptRoot 'run_notebooks.py'
$fontFixer = Join-Path $PSScriptRoot 'fix_notebook_fonts.py'

if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "未找到隔离环境。请先运行：$PSScriptRoot\安装本地环境.ps1"
}
if (-not (Test-Path -LiteralPath $runner -PathType Leaf)) {
    throw "未找到 Notebook 执行器：$runner"
}
if (-not (Test-Path -LiteralPath $fontFixer -PathType Leaf)) {
    throw "未找到 Notebook 字体修复器：$fontFixer"
}

& $pythonPath $fontFixer
if ($LASTEXITCODE -ne 0) {
    throw 'Notebook 字体配置失败。'
}
& $pythonPath $runner
if ($LASTEXITCODE -ne 0) {
    throw 'Notebook 批量执行失败，请查看终端中的首个错误。'
}
Write-Host '全部规范 Notebook 执行与错误检查通过。' -ForegroundColor Green
