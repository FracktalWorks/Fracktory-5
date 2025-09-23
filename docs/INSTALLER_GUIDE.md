# Creating Fracktory Installers

This guide explains how to create MSI and EXE installers for Fracktory after you have successfully built and run it from source.

## Prerequisites

You need to complete the full Conan build process to create the installer packages. This is different from just running from source.

Additionally, you'll need installer creation tools:
- **NSIS** (for .exe installers) 
- **WiX Toolset** (for .msi installers)

## Installing Installer Tools

### NSIS (for .exe installers)
1. Download from: https://nsis.sourceforge.io/Download
2. Install with default options (automatically adds to PATH)
3. Verify installation: Open new PowerShell and run `makensis /VERSION`

### WiX Toolset (for .msi installers)
1. Download WiX Toolset v3.14 from: https://wixtoolset.org/releases/
2. Install and ensure it's added to PATH
3. Verify installation: Open new PowerShell and run `candle /?`

**Note:** You can install both tools or just the one you need. The build process will skip installers for missing tools.

## Complete Build Process

**⚠️ Important Version Update:** Before creating installers, ensure you've updated version numbers in both `conandata.yml` and `latest.json`. See [Changing Cura Version](../README.md#changing-cura-version) for detailed instructions.

**⚠️ Important:** Perform all git clone operations in a separate workspace folder (e.g., `C:\Workspace`) to avoid cloning repositories inside the Fracktory repository.

### Step 1: Setup Conan Environment
First, set up Conan with the exact configuration from the GitHub Actions:

```powershell
# Install Conan
python -m pip install --upgrade pip setuptools wheel
pip install conan==1.65.0
```

### Step 2: Setup Conan Configuration

**Option 1: If conan-config folder doesn't exist (first time):**
```powershell
# Navigate to your workspace folder (NOT inside Fracktory-5)
cd C:\Workspace  # or your preferred workspace location

# Clone and setup Conan config
git clone https://github.com/ultimaker/conan-config.git
cd conan-config
git checkout 3226488623c642b40ca7ce3f62d3f33de046d11e
cd ..
conan config install ./conan-config
conan remote remove cura-private
```

### Step 3: Build CuraEngine
Clone and build the CuraEngine dependency:

**Option 1: If CuraEngine folder doesn't exist (first time):**
```powershell
# Ensure you're in your workspace folder (NOT inside Fracktory-5)
cd C:\Workspace  # or your preferred workspace location

# Clone FracktalWorks CuraEngine
git clone https://github.com/FracktalWorks/CuraEngine.git
cd CuraEngine
git checkout Engine-5.9.1
git pull
conan remove --locks
conan create . curaengine/5.9.1@FracktalWorks/stable --build=missing --update
cd ..
```

**Option 2: If CuraEngine folder already exists:**
```powershell
# Navigate to existing CuraEngine folder
cd C:\Workspace\CuraEngine  # or your CuraEngine location
git checkout Engine-5.9.1
git pull
conan remove --locks
conan create . curaengine/5.9.1@FracktalWorks/stable --build=missing --update
cd ..
```

### Step 4: Create Installer Packages
Navigate to the Fracktory-5 repository and run the complete Conan build process that creates `cura_inst` folder:

**Option 1: If Fracktory-5 repository doesn't exist (first time):**
```powershell
# Ensure you're in your workspace folder
cd C:\Workspace  # or your preferred workspace location

# Clone Fracktory-5 repository
git clone https://github.com/FracktalWorks/Fracktory-5.git
cd Fracktory-5
git checkout Fracktory-5.9
```

**Option 2: If Fracktory-5 repository already exists:**
```powershell
# Navigate to existing Fracktory-5 folder
cd C:\Workspace\Fracktory-5  # or your Fracktory-5 location
git checkout Fracktory-5.9
git pull
```

**Then run the Conan install process:**
```powershell
# Install with virtual Python environment for installer creation
conan install . local/test --require-override=curaengine/5.9.1@FracktalWorks/stable --build=missing --update -if cura_inst -g VirtualPythonEnv -o cura:enterprise=False -o cura:staging=False -o cura:internal=False -c tools.build:skip_test=True -s curaengine:build_type=RelWithDebInfo -s arcus:build_type=RelWithDebInfo -s clipper:build_type=RelWithDebInfo
```

### Step 5: Generate Local Environment Scripts
The GitHub Actions scripts use `$Env:GITHUB_ENV` which doesn't work locally. Generate working local versions:

```powershell
# Generate local versions of the environment activation scripts
.\generate_local_env_scripts.ps1
```

This converts:
- `activate_github_actions_env.ps1` → `activate_local_env.ps1` (sets all Conan paths)
- `activate_github_actions_version_env.ps1` → `activate_local_version_env.ps1` (sets version variables)

### Step 6: Verify Prerequisites
Check that you have everything needed for installer creation:

```powershell
.\check_prerequisites.ps1
```

This will verify:
- ✅ Your source environment works (`cura_inst` exists and Cura modules load)
- ✅ PyInstaller is available
- ✅ NSIS is installed (for .exe installers)
- ✅ WiX Toolset is installed (for .msi installers)

### Step 7: Create Installers

Now you can create the installers using the exact GitHub Actions commands:

```powershell
# 1. Set environment variables (IMPORTANT - must be done FIRST!)
.\cura_inst\Scripts\activate_local_env.ps1
.\cura_inst\Scripts\activate_local_version_env.ps1

# 2. Create the PyInstaller executable
pyinstaller .\cura_inst\Fracktory.spec

# 3. Create NSIS EXE installer (requires NSIS - needs 4-part version)
$env:NSIS_PATH = "C:\Program Files (x86)\NSIS"
$env:Path += ";$env:NSIS_PATH"
.\cura_inst\Scripts\python.exe cura_inst\packaging\NSIS\create_windows_installer.py cura_inst dist "Fracktory-$env:CURA_VERSION_FULL.exe"

# 4. Create WiX MSI installer (requires WiX Toolset - uses 3-part version)
$env:WIX_PATH = "C:\Program Files (x86)\WiX Toolset v3.14\bin"
$env:Path += ";$env:WIX_PATH"
.\cura_inst\Scripts\python.exe cura_inst\packaging\msi\create_windows_msi.py cura_inst dist\Fracktory "dist\Fracktory-$env:CURA_VERSION_FULL.msi" "Fracktory"
```

**Note:** The script automatically reads the version from `conandata.yml`, so your installers will always match your project version.

## What You Get

After successful completion:
- **`dist\Fracktory\Fracktory.exe`** - Standalone executable
- **`Fracktory-{version}.exe`** - NSIS installer (if NSIS available)
- **`Fracktory-{version}.msi`** - MSI installer (if WiX available)

Where `{version}` is automatically read from `conandata.yml` (currently 5.9.9).

## Troubleshooting

**"Virtual environment not found"**
- Follow the main README.md to build from source first
- Ensure you can run `python cura_app.py` successfully

**"Cannot import Cura modules"**
- Your source environment isn't working properly
- Rebuild following the README.md instructions

**"Fracktory.spec not found"**
- This file should be generated during conan install
- Re-run the conan install step from the README

**"PyInstaller not found"**
```powershell
.\venv\Scripts\pip install pyinstaller
```

**Installer creation fails**
- Install NSIS and/or WiX Toolset
- Ensure they are properly added to your system PATH

## Creating a GitHub Release (Optional)

After successfully creating your installers, you can create a GitHub release to distribute them:

### Step 1: Create New Release
1. Go to: https://github.com/FracktalWorks/Fracktory-5/releases/new
2. Fill in the release details:
   - **Tag version**: `v5.9.9` (or your current version)
   - **Release title**: `Fracktory v5.9.9`
   - **Description**: Add changelog, features, and installation instructions

### Step 2: Upload Installer Files
Attach the generated installer files from your build:

**From the `dist` folder:**
- `📁 dist/Fracktory-5.9.9.exe` (NSIS installer)
- `📁 dist/Fracktory-5.9.9.msi` (MSI installer)

### Step 3: Publish Release
1. Mark as **pre-release** if it's a beta/test version
2. Click **"Publish release"**
3. Users can now download installers directly from the GitHub release page

**Note:** Only repository maintainers with write access can create releases. Contributors should create installers for testing and provide them to maintainers for official releases.

## Process Summary

1. **Build from source** (main README.md) → Get working `python cura_app.py`
2. **Install tools** → NSIS and WiX Toolset
3. **Create installers** → Follow Steps 1-6 above
4. **Test installers** → Verify .exe/.msi work on clean systems
5. **Create release** → Upload to GitHub releases (if authorized)
6. **Distribute** → Share release URL or installer files directly

This standardized process ensures you have a working foundation before attempting installer creation.