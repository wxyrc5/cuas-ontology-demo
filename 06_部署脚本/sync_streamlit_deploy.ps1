param(
    [switch]$VerifyOnly
)

$ErrorActionPreference = 'Stop'
$packageRoot = Split-Path -Parent $PSScriptRoot
$sourceRoots = @(
    Get-ChildItem -LiteralPath $packageRoot -Directory | ForEach-Object {
        Join-Path $_.FullName 'streamlit_app'
    } | Where-Object { Test-Path -LiteralPath $_ -PathType Container }
)
$targetRoots = @(
    Get-ChildItem -LiteralPath $packageRoot -Directory | ForEach-Object {
        Join-Path $_.FullName 'streamlit_cloud_deploy'
    } | Where-Object { Test-Path -LiteralPath $_ -PathType Container }
)
if ($sourceRoots.Count -ne 1) {
    throw "Expected exactly one canonical Streamlit app, found $($sourceRoots.Count)."
}
if ($targetRoots.Count -ne 1) {
    throw "Expected exactly one Streamlit deploy mirror, found $($targetRoots.Count)."
}
$sourceRoot = $sourceRoots[0]
$targetRoot = $targetRoots[0]
$managedPaths = @(
    'app.py',
    'demo_mode.py',
    'README.md',
    'requirements.txt',
    'pages',
    'utils',
    'data',
    'static',
    '.streamlit'
)

if (-not (Test-Path -LiteralPath $sourceRoot -PathType Container)) {
    throw "Canonical Streamlit app not found: $sourceRoot"
}
if (-not (Test-Path -LiteralPath $targetRoot -PathType Container)) {
    throw "Cloud deployment directory not found: $targetRoot"
}

$sourceRootResolved = (Resolve-Path -LiteralPath $sourceRoot).Path
$targetRootResolved = (Resolve-Path -LiteralPath $targetRoot).Path
if (-not $sourceRootResolved.StartsWith($packageRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Canonical source resolved outside the package root.'
}
if (-not $targetRootResolved.StartsWith($packageRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Deployment target resolved outside the package root.'
}

$copied = 0
foreach ($managedPath in $managedPaths) {
    $sourcePath = Join-Path $sourceRootResolved $managedPath
    if (-not (Test-Path -LiteralPath $sourcePath)) {
        continue
    }

    $sourceItem = Get-Item -LiteralPath $sourcePath
    $sourceFiles = if ($sourceItem.PSIsContainer) {
        Get-ChildItem -LiteralPath $sourcePath -Recurse -File | Where-Object {
            $_.FullName -notmatch '\\__pycache__\\' -and $_.Extension -ne '.pyc'
        }
    } else {
        @($sourceItem)
    }

    foreach ($sourceFile in $sourceFiles) {
        $relative = $sourceFile.FullName.Substring($sourceRootResolved.Length).TrimStart('\')
        $targetFile = Join-Path $targetRootResolved $relative
        if (-not $VerifyOnly) {
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $targetFile) | Out-Null
            Copy-Item -LiteralPath $sourceFile.FullName -Destination $targetFile -Force
            $copied += 1
        }

        if (-not (Test-Path -LiteralPath $targetFile -PathType Leaf)) {
            throw "Missing deployment mirror file: $relative"
        }
        $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourceFile.FullName).Hash
        $targetHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $targetFile).Hash
        if ($sourceHash -ne $targetHash) {
            throw "Deployment mirror mismatch: $relative"
        }
    }
}

if ($VerifyOnly) {
    Write-Output 'Streamlit deployment mirror verified.'
} else {
    Write-Output "Streamlit deployment mirror synchronized: $copied files."
}
