[CmdletBinding()]
param(
    [switch]$SkipPyInstaller
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$specPath = Join-Path $PSScriptRoot "syllavox.spec"
$buildRoot = Join-Path $projectRoot "build"
$distRoot = Join-Path $buildRoot "portable"
$workRoot = Join-Path $buildRoot "pyinstaller"
$portableRoot = Join-Path $distRoot "Syllavox"
$zipPath = Join-Path $buildRoot "Syllavox-portable.zip"
$projectLicense = Join-Path $projectRoot "LICENSE"
$pyproject = Join-Path $projectRoot "pyproject.toml"
$thirdPartyNotices = Join-Path $projectRoot "THIRD_PARTY_NOTICES.md"
$changelog = Join-Path $projectRoot "CHANGELOG.md"
$trayIcon = Join-Path $projectRoot "src\syllavox\assets\tray_icon.png"
$sitePackagesRoot = Join-Path $projectRoot ".venv\Lib\site-packages"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Project virtual environment was not found at $pythonPath"
}

$requiredFiles = @(
    $specPath,
    $projectLicense,
    $thirdPartyNotices,
    $changelog,
    $trayIcon,
    $pyproject
)

foreach ($requiredFile in $requiredFiles) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Required release file was not found: $requiredFile"
    }
}

if (-not (Test-Path -LiteralPath $sitePackagesRoot -PathType Container)) {
    throw "The virtual environment site-packages directory was not found at $sitePackagesRoot"
}

$versionMatch = Select-String `
    -LiteralPath $pyproject `
    -Pattern '^version\s*=\s*"([^"]+)"' `
    | Select-Object -First 1

if ($null -eq $versionMatch -or $versionMatch.Matches.Count -eq 0) {
    throw "Could not read the project version from $pyproject"
}

$projectVersion = $versionMatch.Matches[0].Groups[1].Value

New-Item -ItemType Directory -Path $buildRoot -Force | Out-Null

$buildRootFull = [System.IO.Path]::GetFullPath($buildRoot)
$portableRootFull = [System.IO.Path]::GetFullPath($portableRoot)
$buildRootPrefix = $buildRootFull.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar

if (-not $portableRootFull.StartsWith(
        $buildRootPrefix,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
    throw "Refusing to remove a portable output outside the build directory: $portableRootFull"
}

if (-not $SkipPyInstaller) {
    if (Test-Path -LiteralPath $portableRoot) {
        Remove-Item -LiteralPath $portableRoot -Recurse -Force
    }

    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }

    & $pythonPath -m PyInstaller `
        --noconfirm `
        --clean `
        --distpath $distRoot `
        --workpath $workRoot `
        $specPath

    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }
}
elseif (-not (Test-Path -LiteralPath (Join-Path $portableRoot "Syllavox.exe") -PathType Leaf)) {
    throw "-SkipPyInstaller was used, but no existing Syllavox.exe was found in $portableRoot"
}

if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

Copy-Item -LiteralPath $projectLicense -Destination $portableRoot -Force
Copy-Item -LiteralPath $thirdPartyNotices -Destination $portableRoot -Force
Copy-Item -LiteralPath $changelog -Destination $portableRoot -Force

$licenseRoot = Join-Path $portableRoot "licenses"
New-Item -ItemType Directory -Path $licenseRoot -Force | Out-Null

$licenseSources = @(
    @{ Pattern = "piper_tts-*.dist-info\licenses\COPYING"; Name = "piper-COPYING" },
    @{ Pattern = "pyside6-*.dist-info\licenses\LicenseRef-Qt-Commercial.txt"; Name = "qt-python-license-reference.txt" },
    @{ Pattern = "pyinstaller-*.dist-info\licenses\COPYING.txt"; Name = "pyinstaller-COPYING.txt" }
)

foreach ($licenseSource in $licenseSources) {
    $matches = Get-ChildItem `
        -Path (Join-Path $projectRoot ".venv\Lib\site-packages\$($licenseSource.Pattern)") `
        -File `
        -ErrorAction SilentlyContinue

    $licenseFile = $matches | Select-Object -First 1
    if ($null -ne $licenseFile) {
        Copy-Item -LiteralPath $licenseFile.FullName `
            -Destination (Join-Path $licenseRoot $licenseSource.Name) `
            -Force
    }
}

$dependencyInventory = Join-Path $portableRoot "DEPENDENCY_VERSIONS.txt"
$inventoryLines = [System.Collections.Generic.List[string]]::new()
$inventoryLines.Add("Syllavox $projectVersion portable build dependency inventory")
$inventoryLines.Add(("Generated UTC: {0}" -f [DateTime]::UtcNow.ToString("o")))
$inventoryLines.Add("Source: the build virtual environment's site-packages metadata")
$inventoryLines.Add("")
$inventoryLines.Add("Package == version")
$inventoryLines.Add("------------------")

Get-ChildItem -LiteralPath $sitePackagesRoot -Directory -Filter "*.dist-info" |
    Sort-Object Name |
    ForEach-Object {
        $metadataPath = Join-Path $_.FullName "METADATA"
        if (-not (Test-Path -LiteralPath $metadataPath -PathType Leaf)) {
            return
        }

        $nameLine = (
            Select-String -LiteralPath $metadataPath -Pattern "^Name:" |
                Select-Object -First 1
        ).Line
        $versionLine = (
            Select-String -LiteralPath $metadataPath -Pattern "^Version:" |
                Select-Object -First 1
        ).Line

        if ($null -ne $nameLine -and $null -ne $versionLine) {
            $packageName = $nameLine.Substring(5).Trim()
            $packageVersion = $versionLine.Substring(8).Trim()
            $inventoryLines.Add("$packageName == $packageVersion")
        }
    }

$inventoryLines | Set-Content -LiteralPath $dependencyInventory -Encoding UTF8

$portableReadme = Join-Path $portableRoot "PORTABLE_README.txt"
@"
Syllavox - portable build

Run Syllavox.exe to start the application.

User settings, logs, temporary audio, and downloaded Piper voices are stored
under %LOCALAPPDATA%\Syllavox and are not part of this folder.
The Chinese g2pW phonemization resource, when needed, is stored there as well
and is downloaded on first use of a Chinese voice.

This build does not include voice models. Install voices explicitly from the
application's voice catalog, or restore them from the project's external
piper_voice_backup directory.

Syllavox code is MIT-licensed, but this portable build contains third-party
components with their own licenses. Read THIRD_PARTY_NOTICES.md and the
licenses folder before redistributing this build. DEPENDENCY_VERSIONS.txt
records the exact packages present in the build environment.
"@ | Set-Content -LiteralPath $portableReadme -Encoding UTF8

if (-not (Test-Path -LiteralPath (Join-Path $portableRoot "Syllavox.exe") -PathType Leaf)) {
    throw "The portable executable was not created in $portableRoot"
}

$allowedEmbeddedModelRoots = @(
    # Piper ships these runtime models as package data. They are not user
    # voice models downloaded through Syllavox's catalog.
    [System.IO.Path]::GetFullPath(
        (Join-Path $portableRoot "_internal\piper\tashkeel")
    ),
    [System.IO.Path]::GetFullPath(
        (Join-Path $portableRoot "_internal\piper\hebrew")
    )
)
$voiceFiles = Get-ChildItem -LiteralPath $portableRoot -Recurse -File |
    Where-Object {
        $filePath = $_.FullName
        $_.Extension -eq ".onnx" -and
        -not ($allowedEmbeddedModelRoots | Where-Object {
            $allowedRoot = $_
            $filePath.StartsWith(
                $allowedRoot + [System.IO.Path]::DirectorySeparatorChar,
                [System.StringComparison]::OrdinalIgnoreCase
            )
        })
    }

if ($voiceFiles.Count -gt 0) {
    throw "Voice model files were found in the portable output; refusing to package them."
}

Add-Type -AssemblyName System.IO.Compression.FileSystem

[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $portableRoot,
    $zipPath,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $false
)

Write-Output "Portable folder: $portableRoot"
Write-Output "Portable ZIP:    $zipPath"
