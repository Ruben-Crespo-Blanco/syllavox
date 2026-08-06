param(
    [string]$BackupRoot = ""
)

$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$projectRoot = Split-Path -Parent $repositoryRoot
if ([string]::IsNullOrWhiteSpace($BackupRoot)) {
    $BackupRoot = Join-Path $projectRoot "piper_voice_backup"
}

$catalogUrl = "https://huggingface.co/rhasspy/piper-voices/resolve/main/voices.json?download=true"
$baseUrl = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
$catalogPath = Join-Path $BackupRoot "voices.json"
$filesRoot = Join-Path $BackupRoot "files"
$manifestPath = Join-Path $BackupRoot "BACKUP_MANIFEST.txt"
$tempCatalogPath = Join-Path ([System.IO.Path]::GetTempPath()) ("syllavox-piper-voices-{0}.json" -f [guid]::NewGuid())

New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
New-Item -ItemType Directory -Path $filesRoot -Force | Out-Null

try {
    & curl.exe --fail --silent --show-error --location --retry 5 --retry-delay 2 --output $tempCatalogPath $catalogUrl
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to download the Piper voice catalog. curl exit code: $LASTEXITCODE"
    }

    $catalog = Get-Content -LiteralPath $tempCatalogPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Copy-Item -LiteralPath $tempCatalogPath -Destination $catalogPath -Force

    $voiceProperties = @($catalog.PSObject.Properties)
    $manifestLines = [System.Collections.Generic.List[string]]::new()
    $manifestLines.Add("Syllavox Piper voice backup")
    $manifestLines.Add("Source: $catalogUrl")
    $manifestLines.Add(("Downloaded UTC: {0}" -f [DateTime]::UtcNow.ToString("o")))
    $manifestLines.Add(("Voices: {0}" -f $voiceProperties.Count))
    $manifestLines.Add("")
    $manifestLines.Add("Relative source path | Size bytes | MD5")
    $manifestLines.Add("-------------------- | ---------- | ---")

    $voiceIndex = 0
    foreach ($voiceProperty in $voiceProperties) {
        $voiceIndex++
        $voiceKey = $voiceProperty.Name
        $fileProperties = @($voiceProperty.Value.files.PSObject.Properties)
        Write-Output ("[{0}/{1}] {2}" -f $voiceIndex, $voiceProperties.Count, $voiceKey)

        foreach ($fileProperty in $fileProperties) {
            $relativePath = [string]$fileProperty.Name
            $expectedSize = [int64]$fileProperty.Value.size_bytes
            $expectedMd5 = ([string]$fileProperty.Value.md5_digest).ToUpperInvariant()
            $relativeWindowsPath = $relativePath.Replace("/", [System.IO.Path]::DirectorySeparatorChar)
            $targetPath = Join-Path $filesRoot $relativeWindowsPath
            $targetDirectory = Split-Path -Parent $targetPath
            New-Item -ItemType Directory -Path $targetDirectory -Force | Out-Null

            $isValid = $false
            if (Test-Path -LiteralPath $targetPath) {
                $existingFile = Get-Item -LiteralPath $targetPath
                if ($existingFile.Length -eq $expectedSize) {
                    $existingMd5 = (Get-FileHash -Algorithm MD5 -LiteralPath $targetPath).Hash.ToUpperInvariant()
                    $isValid = $existingMd5 -eq $expectedMd5
                }
                if (-not $isValid -and $existingFile.Length -ge $expectedSize) {
                    Remove-Item -LiteralPath $targetPath -Force
                }
            }

            if (-not $isValid) {
                $urlPath = (($relativePath -split "/") | ForEach-Object { [Uri]::EscapeDataString($_) }) -join "/"
                $downloadUrl = "${baseUrl}/${urlPath}?download=true"
                & curl.exe --fail --silent --show-error --location --retry 5 --retry-delay 2 --continue-at - --output $targetPath $downloadUrl
                if ($LASTEXITCODE -ne 0) {
                    throw "Unable to download $relativePath. curl exit code: $LASTEXITCODE"
                }

                $downloadedFile = Get-Item -LiteralPath $targetPath
                $downloadedMd5 = (Get-FileHash -Algorithm MD5 -LiteralPath $targetPath).Hash.ToUpperInvariant()
                if ($downloadedFile.Length -ne $expectedSize -or $downloadedMd5 -ne $expectedMd5) {
                    throw "Checksum or size mismatch for $relativePath"
                }
            }

            $manifestLines.Add(("{0} | {1} | {2}" -f $relativePath, $expectedSize, $expectedMd5))
        }
    }

    $catalogHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $catalogPath).Hash
    $manifestLines.Add("")
    $manifestLines.Add("voices.json SHA256 | $catalogHash")
    $manifestLines | Set-Content -LiteralPath $manifestPath -Encoding UTF8
    Write-Output "Backup completed: $BackupRoot"
}
finally {
    if (Test-Path -LiteralPath $tempCatalogPath) {
        Remove-Item -LiteralPath $tempCatalogPath -Force
    }
}
