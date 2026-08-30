[CmdletBinding()]
param(
    [switch]$SkipPortableBuild,
    [switch]$IncludeSherpa
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$portableBuildScript = Join-Path $PSScriptRoot "build_portable.ps1"
$installerScript = Join-Path $PSScriptRoot "Syllavox.iss"
$buildRoot = Join-Path $projectRoot "build"
$portableRoot = Join-Path $buildRoot "portable\Syllavox"
$installerRoot = Join-Path $buildRoot "installer"
$pyproject = Join-Path $projectRoot "pyproject.toml"

foreach ($requiredFile in @($portableBuildScript, $installerScript, $pyproject)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Required release file was not found: $requiredFile"
    }
}

if (-not $SkipPortableBuild) {
    $portableArguments = @("-IncludeSapi")
    if ($IncludeSherpa) {
        $portableArguments += "-IncludeSherpa"
    }

    & powershell.exe -NoProfile -ExecutionPolicy Bypass `
        -File $portableBuildScript @portableArguments
    if ($LASTEXITCODE -ne 0) {
        throw "The portable Syllavox build failed with exit code $LASTEXITCODE."
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $portableRoot "Syllavox.exe") -PathType Leaf)) {
    throw "The portable executable was not found at $portableRoot."
}

$versionMatch = Select-String `
    -LiteralPath $pyproject `
    -Pattern '^version\s*=\s*"([^"]+)"' `
    | Select-Object -First 1

if ($null -eq $versionMatch -or $versionMatch.Matches.Count -eq 0) {
    throw "Could not read the project version from $pyproject."
}

$projectVersion = $versionMatch.Matches[0].Groups[1].Value

$compilerCandidates = @()
if ($env:INNO_SETUP_COMPILER) {
    $compilerCandidates += $env:INNO_SETUP_COMPILER
}

$isccCommand = Get-Command iscc.exe -ErrorAction SilentlyContinue
if ($null -ne $isccCommand) {
    $compilerCandidates += $isccCommand.Source
}

if ($env:ProgramFiles -and $env:ProgramFiles -ne "") {
    $compilerCandidates += Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"
}
if (${env:ProgramFiles(x86)} -and ${env:ProgramFiles(x86)} -ne "") {
    $compilerCandidates += Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
}

$isccPath = $compilerCandidates |
    Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
    Select-Object -First 1

if ($null -eq $isccPath) {
    throw (
        "Inno Setup compiler was not found. Install Inno Setup 6 or set " +
        "INNO_SETUP_COMPILER to the full path of ISCC.exe."
    )
}

New-Item -ItemType Directory -Path $installerRoot -Force | Out-Null

& $isccPath `
    "/DAppVersion=$projectVersion" `
    "/DSourceDir=$portableRoot" `
    "/DOutputDir=$installerRoot" `
    $installerScript

if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup failed with exit code $LASTEXITCODE."
}

$installerPath = Join-Path $installerRoot "Syllavox-$projectVersion-setup.exe"
if (-not (Test-Path -LiteralPath $installerPath -PathType Leaf)) {
    throw "The installer was not created at $installerPath."
}

$hashPath = "$installerPath.sha256"
$hash = (Get-FileHash -LiteralPath $installerPath -Algorithm SHA256).Hash
Set-Content -LiteralPath $hashPath -Value "$hash  $(Split-Path -Leaf $installerPath)" -Encoding ASCII

Write-Output "Windows installer: $installerPath"
Write-Output "SHA-256 file:      $hashPath"
