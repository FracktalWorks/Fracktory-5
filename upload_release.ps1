# GitHub Release Upload Script for AddiSlice 5.9.12
# This script creates a GitHub release and uploads the installer artifacts

param(
    [Parameter(Mandatory=$true)]
    [string]$GitHubToken
)

$ErrorActionPreference = "Stop"

# Configuration
$Owner = "FracktalWorks"
$Repo = "AddiSlice"
$TagName = "v5.9.12"
$ReleaseName = "AddiSlice v5.9.12"
$ReleaseBody = @"
# AddiSlice v5.9.12

## Installation

### Windows Users
Download one of the following installers:
- **AddiSlice-5.9.12.exe** - NSIS installer (recommended for most users)
- **AddiSlice-5.9.12.msi** - MSI installer (for enterprise deployments)

### System Requirements
- Windows 10/11 (64-bit)
- 4GB RAM minimum (8GB recommended)
- OpenGL 4.1 compatible graphics

## What's New in 5.9.12
- Added Penrose 600 IDEX pellet extruder printer
- Pellet extrusion slicer optimization (coasting, speed uniformity, bridge settings)
- 4 pellet materials (PLA, ABS, TPU 95A, Nylon)
- 82 quality profiles for Penrose 600 IDEX (10 global + 72 per-variant)
- CuraEngine 5.9.2 integration
- Bug fixes and performance improvements
"@

# Files to upload
$Files = @(
    "dist\AddiSlice-5.9.12.exe",
    "dist\AddiSlice-5.9.12.msi"
)

$Headers = @{
    "Authorization" = "token $GitHubToken"
    "Accept" = "application/vnd.github.v3+json"
}

# Create the release
Write-Host "Creating GitHub release..." -ForegroundColor Cyan

$ReleaseData = @{
    tag_name = $TagName
    target_commitish = "AddiSlice-5.9"
    name = $ReleaseName
    body = $ReleaseBody
    draft = $false
    prerelease = $false
} | ConvertTo-Json

try {
    $Release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Owner/$Repo/releases" -Method Post -Headers $Headers -Body $ReleaseData -ContentType "application/json"
    Write-Host "Release created successfully!" -ForegroundColor Green
    Write-Host "Release ID: $($Release.id)" -ForegroundColor Yellow
    Write-Host "Release URL: $($Release.html_url)" -ForegroundColor Yellow
} catch {
    if ($_.Exception.Response.StatusCode -eq 422) {
        Write-Host "Release may already exist. Getting existing release..." -ForegroundColor Yellow
        $Release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Owner/$Repo/releases/tags/$TagName" -Headers $Headers
    } else {
        throw $_
    }
}

# Upload assets
$UploadUrl = $Release.upload_url -replace '\{.*\}', ''

foreach ($FilePath in $Files) {
    if (Test-Path $FilePath) {
        $FileName = Split-Path $FilePath -Leaf
        Write-Host "Uploading $FileName..." -ForegroundColor Cyan
        
        $FileBytes = [System.IO.File]::ReadAllBytes((Resolve-Path $FilePath))
        
        $UploadHeaders = @{
            "Authorization" = "token $GitHubToken"
            "Content-Type" = "application/octet-stream"
        }
        
        try {
            $Asset = Invoke-RestMethod -Uri "$UploadUrl`?name=$FileName" -Method Post -Headers $UploadHeaders -Body $FileBytes
            Write-Host "  Uploaded: $($Asset.browser_download_url)" -ForegroundColor Green
        } catch {
            Write-Host "  Failed to upload $FileName : $_" -ForegroundColor Red
        }
    } else {
        Write-Host "File not found: $FilePath" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== Release Complete ===" -ForegroundColor Green
Write-Host "View your release at: $($Release.html_url)" -ForegroundColor Cyan
