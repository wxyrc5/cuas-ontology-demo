param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 8888
)

$ErrorActionPreference = 'Stop'
$packageRoot = Split-Path -Parent $PSScriptRoot
$workspaceRoot = Split-Path -Parent $packageRoot
$notebookRoot = Join-Path $packageRoot '05_Notebook与数据'
$pythonPath = Join-Path $workspaceRoot '.venv-cuas\python.exe'
$jupyterStateRoot = Join-Path $workspaceRoot '.jupyter-cuas'

if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "未找到隔离环境。请先运行：$PSScriptRoot\安装本地环境.ps1"
}
if (-not (Test-Path -LiteralPath $notebookRoot -PathType Container)) {
    throw "未找到 Notebook 目录：$notebookRoot"
}

& $pythonPath -c "import jupyterlab, ipykernel, nbclient, nbformat; print('Jupyter 环境检查通过')"
if ($LASTEXITCODE -ne 0) {
    throw 'Jupyter 依赖检查失败，请重新执行安装本地环境.ps1。'
}

Write-Host "JupyterLab 将使用目录：$notebookRoot" -ForegroundColor Green
Write-Host '按 Ctrl+C 停止服务。' -ForegroundColor DarkGray
$env:JUPYTER_RUNTIME_DIR = Join-Path $jupyterStateRoot 'runtime'
$env:JUPYTER_CONFIG_DIR = Join-Path $jupyterStateRoot 'config'
$env:JUPYTER_DATA_DIR = Join-Path $jupyterStateRoot 'data'
$env:JUPYTER_PATH = Join-Path $jupyterStateRoot 'share\jupyter'
$env:IPYTHONDIR = Join-Path $jupyterStateRoot 'ipython'
New-Item -ItemType Directory -Force -Path $env:JUPYTER_RUNTIME_DIR, $env:JUPYTER_CONFIG_DIR, $env:JUPYTER_DATA_DIR, $env:JUPYTER_PATH, $env:IPYTHONDIR | Out-Null
$kernelSpec = Join-Path $env:JUPYTER_PATH 'kernels\cuas-zx2026\kernel.json'
if (-not (Test-Path -LiteralPath $kernelSpec -PathType Leaf)) {
    & $pythonPath -m ipykernel install --prefix $jupyterStateRoot --name cuas-zx2026 --display-name 'C-UAS Python 3.11'
    if ($LASTEXITCODE -ne 0) {
        throw 'C-UAS Jupyter 内核注册失败。'
    }
}
& $pythonPath -m jupyterlab --notebook-dir $notebookRoot --port $Port --no-browser
