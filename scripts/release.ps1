param(
    [Parameter(Mandatory = $true)]
    [string]$Version,

    [string]$Message,

    [switch]$CommitAll
)

$ErrorActionPreference = "Stop"

if ($Version.StartsWith("v")) {
    $Version = $Version.Substring(1)
}

$tag = "v$Version"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

$initialStatus = git status --porcelain
if ($initialStatus -and -not $CommitAll) {
    Write-Host "There are uncommitted changes. Review them, then either commit manually or rerun with -CommitAll."
    git status --short
    exit 1
}

$appFile = Join-Path $root "RedditMassScraper.py"
$content = Get-Content -LiteralPath $appFile -Raw

if ($content -notmatch 'APP_VERSION = "[^"]+"') {
    throw "Could not find APP_VERSION in RedditMassScraper.py"
}

$updated = $content -replace 'APP_VERSION = "[^"]+"', "APP_VERSION = `"$Version`""
if ($updated -ne $content) {
    Set-Content -LiteralPath $appFile -Value $updated -NoNewline
}

if (-not $Message) {
    $Message = "Release $tag"
}

if ($CommitAll) {
    git add .
} else {
    git add RedditMassScraper.py
}

git diff --cached --quiet
if ($LASTEXITCODE -eq 1) {
    git commit -m $Message
}

git push origin main

$existingTag = git tag --list $tag
if ($existingTag) {
    throw "Tag $tag already exists locally. Use a new version number."
}

$remoteTag = git ls-remote --tags origin $tag
if ($remoteTag) {
    throw "Tag $tag already exists on origin. Use a new version number."
}

git tag $tag
git push origin $tag

Write-Host "Released $tag. GitHub Actions will build and attach RedditMassScraper.exe to the release."
