[CmdletBinding()]
param(
    [switch]$SkipPyInstaller,
    [switch]$IncludeSherpa,
    [switch]$IncludeSapi
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
$hashPath = "$zipPath.sha256"
$projectLicense = Join-Path $projectRoot "LICENSE"
$pyproject = Join-Path $projectRoot "pyproject.toml"
$thirdPartyNotices = Join-Path $projectRoot "THIRD_PARTY_NOTICES.md"
$changelog = Join-Path $projectRoot "CHANGELOG.md"
$trayIcon = Join-Path $projectRoot "src\syllavox\assets\tray_icon.png"
$sapiPreparationScript = Join-Path $PSScriptRoot "prepare_sapi_wrappers.py"
$sitePackagesRoot = Join-Path $projectRoot ".venv\Lib\site-packages"

# The base portable build remains Piper-only to keep its download small. The
# same spec can include the optional native Sherpa runtime and Windows SAPI
# bridge when their switches are explicitly requested.
$env:SYLLAVOX_INCLUDE_SHERPA = if ($IncludeSherpa) { "1" } else { "0" }
$env:SYLLAVOX_INCLUDE_SAPI = if ($IncludeSapi) { "1" } else { "0" }

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

if ($IncludeSapi) {
    $requiredFiles += $sapiPreparationScript
}

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

if ($IncludeSapi -and -not $SkipPyInstaller) {
    & $pythonPath $sapiPreparationScript
    if ($LASTEXITCODE -ne 0) {
        throw "Could not prepare the registered Windows SAPI COM wrappers."
    }
}

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
    if (Test-Path -LiteralPath $hashPath) {
        Remove-Item -LiteralPath $hashPath -Force
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

if ($IncludeSapi) {
    $licenseSources += @(
        @{ Pattern = "comtypes-*.dist-info\licenses\LICENSE*"; Name = "comtypes-LICENSE" },
        @{ Pattern = "comtypes-*.dist-info\licenses\COPYING*"; Name = "comtypes-COPYING" },
        @{ Pattern = "comtypes-*.dist-info\LICENSE*"; Name = "comtypes-LICENSE-root" }
    )
}

if ($IncludeSherpa) {
    $licenseSources += @(
        @{ Pattern = "sherpa_onnx-*.dist-info\licenses\LICENSE"; Name = "sherpa-onnx-LICENSE" },
        @{ Pattern = "sherpa_onnx-*.dist-info\licenses\Apache-2.0.txt"; Name = "sherpa-onnx-Apache-2.0.txt" },
        @{ Pattern = "sherpa_onnx-*.dist-info\LICENSE*"; Name = "sherpa-onnx-LICENSE-root" },
        @{ Pattern = "sherpa_onnx_bin-*.dist-info\licenses\LICENSE"; Name = "sherpa-onnx-bin-LICENSE" },
        @{ Pattern = "sherpa_onnx_bin-*.dist-info\licenses\Apache-2.0.txt"; Name = "sherpa-onnx-bin-Apache-2.0.txt" },
        @{ Pattern = "sherpa_onnx_bin-*.dist-info\LICENSE*"; Name = "sherpa-onnx-bin-LICENSE-root" }
    )
}

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
$bundledRuntimeRoot = Join-Path $portableRoot "_internal"
$inventoryLines = [System.Collections.Generic.List[string]]::new()
$inventoryLines.Add("Syllavox $projectVersion portable build dependency inventory")
$inventoryLines.Add(("Generated UTC: {0}" -f [DateTime]::UtcNow.ToString("o")))
$inventoryLines.Add("Source: bundled portable runtime metadata")
$inventoryLines.Add("")
$inventoryLines.Add("Package == version")
$inventoryLines.Add("------------------")

Get-ChildItem -LiteralPath $bundledRuntimeRoot -Directory -Filter "*.dist-info" |
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

if ($IncludeSapi) {
    $comtypesMetadata = Get-ChildItem `
        -Path (Join-Path $sitePackagesRoot "comtypes-*.dist-info\METADATA") `
        -File `
        -ErrorAction SilentlyContinue `
        | Select-Object -First 1

    if ($null -ne $comtypesMetadata) {
        $comtypesVersionLine = (
            Select-String -LiteralPath $comtypesMetadata.FullName `
                -Pattern "^Version:" `
                | Select-Object -First 1
        ).Line

        if ($null -ne $comtypesVersionLine) {
            $comtypesVersion = $comtypesVersionLine.Substring(8).Trim()
            $inventoryLines.Add("comtypes == $comtypesVersion")
        }
    }
}

$inventoryLines | Set-Content -LiteralPath $dependencyInventory -Encoding UTF8

$portableReadme = Join-Path $portableRoot "PORTABLE_README.txt"
@"
Syllavox $projectVersion - portable build

Run Syllavox.exe to start the application.

User settings, logs, temporary audio, and downloaded Piper voices are stored
under %LOCALAPPDATA%\Syllavox and are not part of this folder.
The Chinese g2pW phonemization resource, when needed, is stored there as well
and is downloaded on first use of a Chinese voice.

This is a Piper-only build unless it was created with -IncludeSherpa and/or
-IncludeSapi. In a Sherpa-enabled build, model bundles are still stored under
%LOCALAPPDATA%\Syllavox\models\sherpa-onnx and are not included here.
In a SAPI-enabled build, Windows system voices are discovered through the
Windows Speech API and are not downloaded or included here.

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

$bundledSherpaRoot = Join-Path $bundledRuntimeRoot "sherpa_onnx"
if ($IncludeSherpa -and -not (Test-Path -LiteralPath $bundledSherpaRoot -PathType Container)) {
    throw "Sherpa packaging was requested, but the bundled Sherpa runtime was not found."
}

if (-not $IncludeSherpa -and (Test-Path -LiteralPath $bundledSherpaRoot)) {
    throw "The Piper-only portable output unexpectedly contains Sherpa runtime files."
}

$bundledComtypesRoot = Join-Path $bundledRuntimeRoot "comtypes"
if ($IncludeSapi -and -not (Test-Path -LiteralPath $bundledComtypesRoot -PathType Container)) {
    throw "SAPI packaging was requested, but the bundled comtypes runtime was not found."
}

if (-not $IncludeSapi -and (Test-Path -LiteralPath $bundledComtypesRoot)) {
    throw "The portable output unexpectedly contains comtypes runtime files."
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

$hash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash
Set-Content -LiteralPath $hashPath -Value "$hash  $(Split-Path -Leaf $zipPath)" -Encoding ASCII

Write-Output "Portable folder: $portableRoot"
Write-Output "Portable ZIP:    $zipPath"
Write-Output "SHA-256 file:    $hashPath"
