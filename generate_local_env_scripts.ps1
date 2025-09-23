# Generate Local Environment Scripts
# This script converts the GitHub Actions environment scripts to local versions

Write-Host "=== Generating Local Environment Scripts ===" -ForegroundColor Cyan

$scriptDir = ".\cura_inst\Scripts"
$githubEnvScript = "$scriptDir\activate_github_actions_env.ps1"
$githubVersionScript = "$scriptDir\activate_github_actions_version_env.ps1"
$localEnvScript = "$scriptDir\activate_local_env.ps1"
$localVersionScript = "$scriptDir\activate_local_version_env.ps1"

# Check if source scripts exist
if (-not (Test-Path $githubEnvScript)) {
    Write-Host "ERROR: $githubEnvScript not found!" -ForegroundColor Red
    Write-Host "Make sure you've run the conan install step that creates cura_inst folder." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $githubVersionScript)) {
    Write-Host "ERROR: $githubVersionScript not found!" -ForegroundColor Red
    exit 1
}

Write-Host "Converting GitHub Actions environment script..." -ForegroundColor Green

# Read the GitHub Actions environment script
$envLines = Get-Content $githubEnvScript

# Start building the local script content
$localEnvLines = @()
$localEnvLines += "# Local version - sets environment variables directly (auto-generated)"
$localEnvLines += "# Generated from activate_github_actions_env.ps1"
$localEnvLines += ""

# Process each line
foreach ($line in $envLines) {
    if ($line -match 'echo "(.+?)=(.+?)" >> \$Env:GITHUB_ENV') {
        $varName = $matches[1]
        $varValue = $matches[2]
        
        # Convert to local environment variable setting
        if ($varName -eq "PYTHONHOME" -and $varValue -eq "") {
            $localEnvLines += "`$env:$varName = `"`""
        } else {
            $localEnvLines += "`$env:$varName = `"$varValue`""
        }
    }
}

# Add status messages
$localEnvLines += ""
$localEnvLines += "Write-Host `"Set complete Cura environment variables:`" -ForegroundColor Green"
$localEnvLines += "Write-Host `"  VIRTUAL_ENV = `$env:VIRTUAL_ENV`" -ForegroundColor Cyan"
$localEnvLines += "Write-Host `"  PYTHONPATH includes Conan packages and PyQt6`" -ForegroundColor Cyan"
$localEnvLines += "Write-Host `"  PATH includes all Conan binaries and PyQt6 plugins`" -ForegroundColor Cyan"

# Write the local environment script
$localEnvLines | Out-File -FilePath $localEnvScript -Encoding UTF8
Write-Host "Created: $localEnvScript" -ForegroundColor Green

Write-Host "Converting GitHub Actions version script..." -ForegroundColor Green

# Read the GitHub Actions version script
$versionLines = Get-Content $githubVersionScript

# Start building the local version script content
$localVersionLines = @()
$localVersionLines += "# Local version - sets version environment variables directly (auto-generated)"
$localVersionLines += "# Generated from activate_github_actions_version_env.ps1"
$localVersionLines += ""

# Process each line
foreach ($line in $versionLines) {
    if ($line -match 'echo "(.+?)=(.+?)" >> \$Env:GITHUB_ENV') {
        $varName = $matches[1]
        $varValue = $matches[2]
        
        # Keep original version format - don't modify CURA_VERSION_FULL
        # The 4-part version conversion will be done only when needed for NSIS
        $localVersionLines += "`$env:$varName = `"$varValue`""
    }
}

# Add status messages
$localVersionLines += ""
$localVersionLines += "Write-Host `"Set Cura version environment variables:`" -ForegroundColor Green"
$localVersionLines += "Write-Host `"  CURA_VERSION_FULL = `$env:CURA_VERSION_FULL`" -ForegroundColor Cyan"
$localVersionLines += "Write-Host `"  CURA_VERSION_MAJOR = `$env:CURA_VERSION_MAJOR`" -ForegroundColor Cyan"
$localVersionLines += "Write-Host `"  CURA_VERSION_MINOR = `$env:CURA_VERSION_MINOR`" -ForegroundColor Cyan"
$localVersionLines += "Write-Host `"  CURA_VERSION_PATCH = `$env:CURA_VERSION_PATCH`" -ForegroundColor Cyan"
$localVersionLines += "Write-Host `"  CURA_APP_NAME = `$env:CURA_APP_NAME`" -ForegroundColor Cyan"

# Write the local version script
$localVersionLines | Out-File -FilePath $localVersionScript -Encoding UTF8
Write-Host "Created: $localVersionScript" -ForegroundColor Green

Write-Host ""
Write-Host "=== Generation Complete ===" -ForegroundColor Cyan
Write-Host "Local scripts created:" -ForegroundColor White
Write-Host "  - $localEnvScript" -ForegroundColor White
Write-Host "  - $localVersionScript" -ForegroundColor White

Write-Host ""
Write-Host "To use the local scripts:" -ForegroundColor Yellow
Write-Host "  .\cura_inst\Scripts\activate_local_env.ps1" -ForegroundColor White
Write-Host "  .\cura_inst\Scripts\activate_local_version_env.ps1" -ForegroundColor White

Write-Host ""
Write-Host "These scripts set environment variables directly instead of writing to GITHUB_ENV." -ForegroundColor Cyan