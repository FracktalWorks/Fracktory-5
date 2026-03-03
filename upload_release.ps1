# GitHub Release Upload Script for Fracktory 5.9.10
# This script creates a GitHub release and uploads the installer artifacts

param(
    [Parameter(Mandatory=$true)]
    [string]$GitHubToken
)

$ErrorActionPreference = "Stop"

# Configuration
$Owner = "FracktalWorks"
$Repo = "Fracktory-5"
$TagName = "v5.9.10"
$ReleaseName = "Fracktory v5.9.10"
$ReleaseBody = @"
# Fracktory v5.9.10

## Installation

### Windows Users
Download one of the following installers:
- **Fracktory-5.9.10.exe** (277 MB) - NSIS installer (recommended for most users)
- **Fracktory-5.9.10.msi** (377 MB) - MSI installer (for enterprise deployments)

### System Requirements
- Windows 10/11 (64-bit)
- 4GB RAM minimum (8GB recommended)
- OpenGL 4.1 compatible graphics

## What's New in 5.9.10
- CuraEngine 5.9.2 integration
- Bug fixes and performance improvements

## Checksums
After downloading, you can verify the file integrity using the checksums below:

``````
Fracktory-5.9.10.exe - SHA256: D21B73C3CA1255C362D28EA4C3AD5BED8D6D0B71E9E13FF6A6D1D1137408C1BC
Fracktory-5.9.10.msi - SHA256: 1CBCD5082667803049E722525C8BA0BB8F0FCA5EF97E96CFD441D6B257B73538
``````
"@

# Files to upload
$Files = @(
    "dist\Fracktory-5.9.10.exe",
    "dist\Fracktory-5.9.10.msi"
)

$Headers = @{
    "Authorization" = "token $GitHubToken"
    "Accept" = "application/vnd.github.v3+json"
}

# Create the release
Write-Host "Creating GitHub release..." -ForegroundColor Cyan

$ReleaseData = @{
    tag_name = $TagName
    target_commitish = "Fracktory-5.9"
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
