$ErrorActionPreference = "Stop"

$extensionRoot = $PSScriptRoot
$repositoryRoot = Split-Path -Parent $extensionRoot
$buildRoot = Join-Path $repositoryRoot "build\firefox"
$packageRoot = Join-Path $buildRoot "Syllavox"
$zipPath = Join-Path $buildRoot "Syllavox-firefox.zip"

New-Item -ItemType Directory -Path $buildRoot -Force | Out-Null
if (Test-Path -LiteralPath $packageRoot) {
    Remove-Item -LiteralPath $packageRoot -Recurse -Force
}
if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

New-Item -ItemType Directory -Path $packageRoot -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $extensionRoot "background.js") -Destination $packageRoot
Copy-Item -LiteralPath (Join-Path $extensionRoot "content.js") -Destination $packageRoot
Copy-Item -LiteralPath (Join-Path $extensionRoot "manifest.firefox.json") -Destination (Join-Path $packageRoot "manifest.json")
Copy-Item -LiteralPath (Join-Path $extensionRoot "icons") -Destination $packageRoot -Recurse

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $packageRoot,
    $zipPath,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $false
)

Write-Output "Firefox package folder: $packageRoot"
Write-Output "Firefox package ZIP:    $zipPath"
