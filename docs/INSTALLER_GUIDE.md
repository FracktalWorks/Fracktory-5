# Creating Fracktory Installers

This guide explains how to create MSI and EXE installers for Fracktory. It covers the complete process from a clean slate, including removing any existing build artifacts.

## Prerequisites

### Required Software
- **Python 3.10+** with pip
- **Conan 1.x** (version 1.58.0 to <2.0.0)
- **Git** for cloning repositories

### Installer Creation Tools
- **NSIS** (for .exe installers) - Nullsoft Scriptable Install System
- **WiX Toolset v3.14** (for .msi installers) - Windows Installer XML
- **GitHub CLI** (optional, for uploading releases)

## Installing Required Tools

### NSIS (for .exe installers)
1. Download from: https://nsis.sourceforge.io/Download
2. Install to default location: `C:\Program Files (x86)\NSIS`
3. Verify installation:
   ```powershell
   & "C:\Program Files (x86)\NSIS\makensis.exe" /VERSION
   ```

### WiX Toolset (for .msi installers)
1. Download WiX Toolset v3.14 from: https://github.com/wixtoolset/wix3/releases
2. Install to default location: `C:\Program Files (x86)\WiX Toolset v3.14`
3. Verify installation:
   ```powershell
   & "C:\Program Files (x86)\WiX Toolset v3.14\bin\candle.exe" -?
   ```

### GitHub CLI (for uploading releases)
```powershell
winget install GitHub.cli --accept-package-agreements --accept-source-agreements
```

After installation, authenticate:
```powershell
$env:Path += ";C:\Program Files\GitHub CLI"
gh auth login
```

## Complete Build Process (Clean Rebuild)

**⚠️ Important Version Update:** Before creating installers, ensure you've updated version numbers in both `conandata.yml` and `latest.json`. See [Changing Cura Version](../README.md#changing-cura-version) for detailed instructions.

**⚠️ Important:** Perform all git clone operations in a separate workspace folder (e.g., `C:\Workspace`) to avoid cloning repositories inside the Fracktory repository.

### Step 1: Clean Up Existing Build Artifacts

Before starting a fresh build, remove any existing installation folders and build artifacts:

```powershell
# Set your Fracktory-5 location
$fracktoryPath = "C:\path\to\Fracktory-5"  # Change this to your actual path
cd $fracktoryPath

# Remove old Conan installation folder
if (Test-Path "cura_inst") { Remove-Item -Recurse -Force "cura_inst" }

# Remove old PyInstaller build output
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }

# Remove old MSI build artifacts
if (Test-Path "build_msi") { Remove-Item -Recurse -Force "build_msi" }

# Remove old generated files
Remove-Item -Force "*.msi" -ErrorAction SilentlyContinue
Remove-Item -Force "*.wixpdb" -ErrorAction SilentlyContinue
Remove-Item -Force "HeatFile.wxs" -ErrorAction SilentlyContinue
Remove-Item -Force "Fracktory.wxs" -ErrorAction SilentlyContinue

# Remove any old virtual environment folders
if (Test-Path "venv") { Remove-Item -Recurse -Force "venv" }
if (Test-Path ".venv") { Remove-Item -Recurse -Force ".venv" }

Write-Host "Cleanup complete!" -ForegroundColor Green
```

### Step 2: Setup Conan Environment

```powershell
# Install Conan (if not already installed)
pip install "conan>=1.58.0,<2.0.0"

# Verify Conan version
conan --version
```

### Step 3: Setup Conan Configuration

```powershell
# Navigate to your workspace folder (NOT inside Fracktory-5)
cd C:\Workspace  # or your preferred workspace location

# Clone and setup Conan config (if not already done)
if (-not (Test-Path "conan-config")) {
    git clone https://github.com/ultimaker/conan-config.git
}
cd conan-config
git checkout 3226488623c642b40ca7ce3f62d3f33de046d11e
cd ..
conan config install ./conan-config
conan remote remove cura-private -f
```

### Step 4: Build CuraEngine

**⚠️ Version Note:** The CuraEngine version must match the requirement in `conandata.yml`. Check the file for the current required version (e.g., `curaengine/5.9.2`).

```powershell
# Ensure you're in your workspace folder (NOT inside Fracktory-5)
cd C:\Workspace

# Clone or update CuraEngine
if (-not (Test-Path "CuraEngine")) {
    git clone https://github.com/FracktalWorks/CuraEngine.git
}
cd CuraEngine

# Check conandata.yml for the required CuraEngine version
# Use the corresponding branch (e.g., Engine-5.9.2 for curaengine/5.9.2)
git checkout Engine-5.9.2
git pull

# Build CuraEngine with Conan (version must match conandata.yml requirement)
conan remove --locks
conan create . curaengine/5.9.2@FracktalWorks/stable --build=missing --update
cd ..
```

### Step 5: Run Conan Install for Fracktory

```powershell
# Navigate to Fracktory-5 repository
cd $fracktoryPath  # Use the path set in Step 1

# Pull latest changes
git checkout Fracktory-5.9
git pull

# Run Conan install (creates cura_inst folder with all dependencies)
conan install . local/test --require-override=curaengine/5.9.2@FracktalWorks/stable --build=missing --update -if cura_inst -g VirtualPythonEnv -o cura:enterprise=False -o cura:staging=False -o cura:internal=False -c tools.build:skip_test=True -s curaengine:build_type=RelWithDebInfo -s arcus:build_type=RelWithDebInfo -s clipper:build_type=RelWithDebInfo
```

### Step 6: Sync Resources

After Conan install, sync the local resources to ensure all printer definitions and materials are included:

```powershell
# Copy local resources to the cura_inst share folder
$sourceResources = "resources"
$destResources = "cura_inst\share\cura\resources"

# Sync definitions (including custom printers like Volterra 300 ALF)
Copy-Item -Path "$sourceResources\definitions\*" -Destination "$destResources\definitions\" -Recurse -Force

# Sync extruders
Copy-Item -Path "$sourceResources\extruders\*" -Destination "$destResources\extruders\" -Recurse -Force

# Sync materials
Copy-Item -Path "$sourceResources\materials\*" -Destination "$destResources\materials\" -Recurse -Force

# Sync quality profiles
Copy-Item -Path "$sourceResources\quality\*" -Destination "$destResources\quality\" -Recurse -Force

# Sync variants
Copy-Item -Path "$sourceResources\variants\*" -Destination "$destResources\variants\" -Recurse -Force

# Sync intent profiles
Copy-Item -Path "$sourceResources\intent\*" -Destination "$destResources\intent\" -Recurse -Force

Write-Host "Resources synced successfully!" -ForegroundColor Green
```

### Step 7: Generate Local Environment Scripts

```powershell
# Generate local versions of the environment activation scripts
.\generate_local_env_scripts.ps1
```

This converts:
- `activate_github_actions_env.ps1` → `activate_local_env.ps1`
- `activate_github_actions_version_env.ps1` → `activate_local_version_env.ps1`

### Step 8: Activate Environment and Set Version Variables

```powershell
# Activate the Conan environment
.\cura_inst\Scripts\activate_local_env.ps1
.\cura_inst\Scripts\activate_local_version_env.ps1

# Verify version is set correctly
Write-Host "Building Fracktory version: $env:CURA_VERSION_FULL"
```

### Step 9: Create PyInstaller Executable

```powershell
# Run PyInstaller to create the distributable folder
.\cura_inst\Scripts\python.exe -m PyInstaller .\cura_inst\Fracktory.spec

# Verify the output
Get-ChildItem "dist\Fracktory\Fracktory.exe"
```

This creates `dist\Fracktory\` containing the standalone application (~1.3 GB).

**Important:** The PyInstaller build copies resources from `cura_inst\share\cura\resources`. Since we synced our custom resources in Step 6, they will be included automatically. Verify your custom printer definitions are present:

```powershell
# Verify custom printers are included (e.g., Volterra 300 ALF)
Test-Path "dist\Fracktory\share\cura\resources\definitions\volterra_300_alf.def.json"
```

### Step 10: Create NSIS Installer (.exe)

The NSIS installer uses LZMA compression and takes significant time (~10-15 minutes).

```powershell
# Set NSIS path
$nsisPath = "C:\Program Files (x86)\NSIS"

# Create the NSIS installer
# Note: This runs for a long time due to LZMA compression
& "$nsisPath\makensis.exe" /V4 "dist\Fracktory.nsi"

# The output will be: dist\Fracktory-{version}-Windows-X64.exe
```

**Alternative: Run as Background Job** (allows you to continue working):
```powershell
$fracktoryPath = "C:\path\to\Fracktory-5"  # Your Fracktory-5 location
$job = Start-Job -ScriptBlock {
    param($path)
    Set-Location $path
    & "C:\Program Files (x86)\NSIS\makensis.exe" /V4 "dist\Fracktory.nsi" 2>&1 | 
        Out-File "nsis_build.log"
} -ArgumentList $fracktoryPath

# Check job status
Get-Job $job.Id | Select-Object State

# When complete, check the log
Get-Content "nsis_build.log" -Tail 20
```

### Step 11: Create WiX MSI Installer (.msi)

The WiX MSI creation requires running three commands manually. The Python wrapper script may not pass environment variables correctly.

```powershell
# Ensure jinja2 is installed (required for template rendering)
.\cura_inst\Scripts\pip.exe install jinja2 -q

# Set WiX path
$wixPath = "C:\Program Files (x86)\WiX Toolset v3.14\bin"

# Set version variables (ensure these match your version)
$version = $env:CURA_VERSION_FULL  # e.g., "5.9.10"

# Create build_msi output directory
New-Item -ItemType Directory -Force -Path "build_msi"

# Step 11a: Run heat.exe to harvest files from dist\Fracktory
& "$wixPath\heat.exe" dir "dist\Fracktory\" `
    -dr APPLICATIONFOLDER `
    -cg NewFilesGroup `
    -sw5150 `
    -gg -g1 -sf -srd `
    -var "var.CuraDir" `
    -t "ExcludeComponents.xslt" `
    -out "HeatFile.wxs"

# Step 11b: Generate Fracktory.wxs from Jinja template
.\cura_inst\Scripts\python.exe -c @"
import os
from jinja2 import Template
from datetime import datetime
import uuid

source_path = os.getcwd()
app_name = 'Fracktory'
version = '$version'
version_parts = version.split('.')

with open('packaging/msi/Fracktory.wxs.jinja', 'r') as f:
    template = Template(f.read())

wxs_content = template.render(
    app_name=app_name,
    main_app='Fracktory.exe',
    version=version,
    version_major=version_parts[0],
    version_minor=version_parts[1],
    version_patch=version_parts[2] if len(version_parts) > 2 else '0',
    company='Fracktal',
    web_site='https://fracktal.in',
    year=datetime.now().year,
    upgrade_code=str(uuid.uuid5(uuid.NAMESPACE_DNS, app_name)),
    cura_license_file=f'{source_path}/packaging/msi/cura_license.rtf',
    cura_banner_top=f'{source_path}/packaging/msi/banner_top.bmp',
    cura_banner_side=f'{source_path}/packaging/msi/banner_side.bmp',
    cura_icon=f'{source_path}/packaging/icons/Cura.ico',
)

with open('Fracktory.wxs', 'w') as f:
    f.write(wxs_content)
print('Generated Fracktory.wxs')
"@

# Step 11c: Run candle.exe to compile WiX source files
& "$wixPath\candle.exe" -arch x64 `
    "-dCuraDir=dist\Fracktory\" `
    -ext WixFirewallExtension `
    -out "build_msi\" `
    "Fracktory.wxs" "HeatFile.wxs"

# Step 11d: Run light.exe to link and create the MSI
# Note: This takes significant time with high compression
& "$wixPath\light.exe" `
    "build_msi\Fracktory.wixobj" `
    "build_msi\HeatFile.wixobj" `
    -sw1076 `
    "-dcl:high" `
    -sval `
    -ext WixUIExtension `
    -ext WixFirewallExtension `
    -out "Fracktory-$version-Windows-X64.msi"

# The output will be: Fracktory-{version}-Windows-X64.msi in the project root
```

## What You Get

After successful completion:
- **`dist\Fracktory\`** - Standalone application folder (~1.3 GB)
- **`dist\Fracktory-{version}-Windows-X64.exe`** - NSIS installer (~280 MB)
- **`Fracktory-{version}-Windows-X64.msi`** - MSI installer (~380 MB)

Where `{version}` is read from `conandata.yml` (e.g., 5.9.10).

## Troubleshooting

### "cura_inst folder not found"
- Run the Conan install step (Step 5)
- Ensure Conan completed without errors

### "Cannot import Cura modules"
- Your Conan environment isn't set up properly
- Re-run Conan install with `--build=missing`

### "Fracktory.spec not found"
- This file is generated during Conan install
- Re-run Step 5 (Conan install)

### "PyInstaller not found"
```powershell
.\cura_inst\Scripts\pip.exe install pyinstaller
```

### "NSIS makensis.exe not found"
- Verify NSIS is installed at `C:\Program Files (x86)\NSIS`
- Use the full path: `& "C:\Program Files (x86)\NSIS\makensis.exe"`

### "WiX heat/candle/light not found"
- Verify WiX is installed at `C:\Program Files (x86)\WiX Toolset v3.14`
- Use full paths as shown in Step 11

### "WiX MSI Python script fails with 'None.None.None' version"
- The Python wrapper script doesn't receive environment variables properly
- Use the manual WiX commands in Step 11 instead

### "NSIS build is interrupted"
- Run NSIS as a background job (see Step 10 alternative)
- Don't run other terminal commands while NSIS is compressing

### "jinja2 module not found"
```powershell
.\cura_inst\Scripts\pip.exe install jinja2
```

## Uploading to GitHub Release

After creating your installers, upload them to GitHub using the CLI:

### Step 1: Install and Authenticate GitHub CLI
```powershell
# Install (if not done earlier)
winget install GitHub.cli --accept-package-agreements

# Add to PATH and authenticate
$env:Path += ";C:\Program Files\GitHub CLI"
gh auth login

# Set default repository
gh repo set-default FracktalWorks/Fracktory-5
```

### Step 2: View Existing Release
```powershell
gh release view $env:CURA_VERSION_FULL
```

### Step 3: Upload Installers
```powershell
# Delete old assets if they exist (use actual asset names from release)
gh release delete-asset $env:CURA_VERSION_FULL "Fracktory-$env:CURA_VERSION_FULL-Windows-X64.exe" --yes 2>$null
gh release delete-asset $env:CURA_VERSION_FULL "Fracktory-$env:CURA_VERSION_FULL-Windows-X64.msi" --yes 2>$null

# Upload new installers
gh release upload $env:CURA_VERSION_FULL `
    "dist\Fracktory-$env:CURA_VERSION_FULL-Windows-X64.exe" `
    "Fracktory-$env:CURA_VERSION_FULL-Windows-X64.msi" `
    --clobber

# Verify upload
gh release view $env:CURA_VERSION_FULL
```

### Creating a New Release (if it doesn't exist)
```powershell
gh release create $env:CURA_VERSION_FULL `
    "dist\Fracktory-$env:CURA_VERSION_FULL-Windows-X64.exe" `
    "Fracktory-$env:CURA_VERSION_FULL-Windows-X64.msi" `
    --title "Fracktory $env:CURA_VERSION_FULL" `
    --notes "Fracktory version $env:CURA_VERSION_FULL release"
```

## Process Summary

1. **Clean up** → Remove old `cura_inst`, `dist`, `build`, and generated files
2. **Setup Conan** → Install and configure Conan with Ultimaker config
3. **Build CuraEngine** → Create CuraEngine Conan package
4. **Conan Install** → Create `cura_inst` folder with all dependencies
5. **Sync Resources** → Copy local printer definitions and materials
6. **Activate Environment** → Set up paths and version variables
7. **PyInstaller** → Create standalone application folder
8. **NSIS Installer** → Create .exe installer (~280 MB)
9. **WiX MSI Installer** → Create .msi installer (~380 MB)
10. **Upload** → Push to GitHub release

**Estimated Total Time:** 45-90 minutes (depending on system and whether Conan packages need rebuilding)

---

## Quick Reference

### Key Paths
| Item | Location |
|------|----------|
| Conan install folder | `cura_inst/` |
| PyInstaller output | `dist/Fracktory/` |
| NSIS installer | `dist/Fracktory-{version}-Windows-X64.exe` |
| MSI installer | `Fracktory-{version}-Windows-X64.msi` (project root) |
| Local resources | `resources/` |
| WiX templates | `packaging/msi/` |
| NSIS templates | Generated in `dist/` during PyInstaller |

### Key Commands (Quick Copy)
```powershell
# Conan install
conan install . local/test --require-override=curaengine/5.9.2@FracktalWorks/stable --build=missing --update -if cura_inst -g VirtualPythonEnv -o cura:enterprise=False -o cura:staging=False -o cura:internal=False -c tools.build:skip_test=True -s curaengine:build_type=RelWithDebInfo -s arcus:build_type=RelWithDebInfo -s clipper:build_type=RelWithDebInfo

# PyInstaller
.\cura_inst\Scripts\python.exe -m PyInstaller .\cura_inst\Fracktory.spec

# NSIS
& "C:\Program Files (x86)\NSIS\makensis.exe" /V4 "dist\Fracktory.nsi"

# WiX (heat → candle → light)
& "C:\Program Files (x86)\WiX Toolset v3.14\bin\heat.exe" dir "dist\Fracktory\" -dr APPLICATIONFOLDER -cg NewFilesGroup -sw5150 -gg -g1 -sf -srd -var "var.CuraDir" -t "ExcludeComponents.xslt" -out "HeatFile.wxs"
& "C:\Program Files (x86)\WiX Toolset v3.14\bin\candle.exe" -arch x64 "-dCuraDir=dist\Fracktory\" -ext WixFirewallExtension -out "build_msi\" "Fracktory.wxs" "HeatFile.wxs"
& "C:\Program Files (x86)\WiX Toolset v3.14\bin\light.exe" "build_msi\Fracktory.wixobj" "build_msi\HeatFile.wixobj" -sw1076 "-dcl:high" -sval -ext WixUIExtension -ext WixFirewallExtension -out "Fracktory-$version-Windows-X64.msi"
```

### Version Configuration
Ensure these files have matching version numbers before building:
- `conandata.yml` - Main version source (e.g., `version: "5.9.10"`)
- `latest.json` - Update checker version
- CuraEngine branch - Should match (e.g., `Engine-5.9.2` for curaengine/5.9.2)