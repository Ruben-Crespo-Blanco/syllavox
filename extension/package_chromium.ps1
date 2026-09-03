$ErrorActionPreference = "Stop"

$extensionRoot = $PSScriptRoot
$repositoryRoot = Split-Path -Parent $extensionRoot
$buildRoot = Join-Path $repositoryRoot "build\chromium"
$packageRoot = Join-Path $buildRoot "Syllavox"
$zipPath = Join-Path $buildRoot "Syllavox-chromium.zip"
$hashPath = "$zipPath.sha256"

$buildRootFull = [System.IO.Path]::GetFullPath($buildRoot)
$packageRootFull = [System.IO.Path]::GetFullPath($packageRoot)
$buildRootPrefix = $buildRootFull.TrimEnd(
    [System.IO.Path]::DirectorySeparatorChar
) + [System.IO.Path]::DirectorySeparatorChar
if (-not $packageRootFull.StartsWith(
        $buildRootPrefix,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
    throw "Refusing to replace a package folder outside the build directory: $packageRootFull"
}

New-Item -ItemType Directory -Path $buildRoot -Force | Out-Null
if (Test-Path -LiteralPath $packageRoot) {
    Remove-Item -LiteralPath $packageRoot -Recurse -Force
}
if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
if (Test-Path -LiteralPath $hashPath) {
    Remove-Item -LiteralPath $hashPath -Force
}

New-Item -ItemType Directory -Path $packageRoot -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $extensionRoot "background.js") -Destination $packageRoot
Copy-Item -LiteralPath (Join-Path $extensionRoot "manifest.json") -Destination $packageRoot
Copy-Item -LiteralPath (Join-Path $extensionRoot "icons") -Destination $packageRoot -Recurse

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $packageRoot,
    $zipPath,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $false
)
$hash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash
Set-Content -LiteralPath $hashPath -Value "$hash  $(Split-Path -Leaf $zipPath)" -Encoding ASCII

Write-Output "Chromium package folder: $packageRoot"
Write-Output "Chromium package ZIP:    $zipPath"
Write-Output "SHA-256 file:            $hashPath"
