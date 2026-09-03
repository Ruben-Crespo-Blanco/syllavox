[CmdletBinding()]
param(
    [string]$Remote = "origin",
    [string]$Tag = "v1.0.0",
    [string]$Message = "release: v1.0.0",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot

function Invoke-Git {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    & git @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

$branch = (& git branch --show-current).Trim()
if ([string]::IsNullOrWhiteSpace($branch)) {
    throw "Refusing to release from a detached HEAD. Check out the release branch first."
}

$projectVersion = Select-String -Path (Join-Path $repoRoot "pyproject.toml") -Pattern '^version\s*=\s*"([^"]+)"' |
    Select-Object -First 1
if ($null -eq $projectVersion -or $projectVersion.Matches[0].Groups[1].Value -ne "1.0.0") {
    throw "pyproject.toml does not declare version 1.0.0."
}

if ((& git tag --list $Tag).Trim()) {
    throw "Tag $Tag already exists locally. Choose a different tag or remove it deliberately."
}

Invoke-Git @("diff", "--check")
$changes = @(git status --porcelain)
if ($changes.Count -eq 0) {
    throw "There are no working-tree changes to release."
}

Write-Host "Preparing $Tag from branch $branch. The following changes will be committed:"
$changes | ForEach-Object { Write-Host "  $_" }
$confirmation = Read-Host "Type RELEASE $Tag to stage, commit, and tag this tree"
if ($confirmation -ne "RELEASE $Tag") {
    throw "Release cancelled."
}

Invoke-Git @("add", "--all")
Invoke-Git @("diff", "--cached", "--check")
Invoke-Git @("commit", "-m", $Message)
Invoke-Git @("tag", "-a", $Tag, "-m", "Syllavox $Tag")

if (-not $SkipPush) {
    Invoke-Git @("push", $Remote, "HEAD")
    Invoke-Git @("push", $Remote, $Tag)
    Write-Host "Released $Tag to $Remote."
} else {
    Write-Host "Created commit and local tag $Tag. Push was skipped."
}
