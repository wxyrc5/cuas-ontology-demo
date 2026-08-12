$ErrorActionPreference = "Stop"
$controlledPython = [System.IO.Path]::GetFullPath(
    (Join-Path $PSScriptRoot "..\..\.venv-cuas\python.exe")
)
if (-not (Test-Path -LiteralPath $controlledPython)) {
    throw "Controlled Python not found: $controlledPython"
}
& $controlledPython (Join-Path $PSScriptRoot "verify_hashes.py")
exit $LASTEXITCODE
