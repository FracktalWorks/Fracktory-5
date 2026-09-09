# AddiSlice
*A 3D printing slicer based on Ultimaker Cura, customized for AddiPrint 3D printers*

## 📚 Documentation

### 🔧 Build and Installation Guides
- **[Prerequisites](#prerequisites)** - Required tools and software for building AddiSlice
- **[Building from Source](#building-from-source)** - Instructions for compiling AddiSlice from source code
- **[Creating Installers](#creating-installers)** - Quick guide to building MSI and EXE installers  
- **[Version Management](#version-management)** - How to update version numbers for new releases

### 📋 Detailed Guides
- **[Installer Guide](docs/INSTALLER_GUIDE.md)** - Complete step-by-step instructions for creating MSI and EXE installers
- **[Update Guide](docs/UPDATING.md)** - Instructions for updating AddiSlice from the latest Cura fork changes
- **[CI/CD Setup Guide](docs/CICD_SETUP.md)** - GitHub Actions and self-hosted runner configuration

### 📄 Project Information
- **[Contributing Guidelines](CONTRIBUTING.md)** - How to contribute to the AddiSlice project
- **[Security Policy](SECURITY.md)** - Reporting security vulnerabilities

### 🔧 Additional Resources
- **[Printer Profile Management](#printer-profile-management)** - Understanding Cura's configuration system and adding printers/materials
- **[AI Agent Guide](docs/agents.md)** - Comprehensive guide for AI agents on creating/editing printer profiles, start/end gcode, temperature settings, and barrel heater integration
- **[Start GCode Generator](#start-gcode-generator)** - Reusable script for generating start/end gcode expressions
- **[Printer Linter](printer-linter/README.md)** - Tool for validating printer definition files
- **[Internationalization](resources/i18n/README.md)** - Translation and localization information
- **Plugin Documentation** - Individual plugin READMEs in the `plugins/` directory

---

## 🚀 Development Setup

## Prerequisites

The following programs are required for building AddiSlice from source on Windows (based on [Ultimaker Cura requirements](https://github.com/Ultimaker/Cura/wiki/Getting-Started)):

- Windows 10 or higher
- Visual Studio with MSVC 2022 or higher
- Python 3.12 or higher
- venv (Python)
- sip (Python) 6.5.1
- CMake 3.23 or higher
- Ninja 1.10 or higher
- Conan >=2.7.0 <3.0.0

#### ✅ Tested Build Environment

The following specific versions have been tested and work reliably:

| Tool | Tested Version | Download Link |
|------|----------------|---------------|
| **Visual Studio** | 17.9.5 | [Release History](https://learn.microsoft.com/en-us/visualstudio/releases/2022/release-history) \| [Direct Download](https://download.visualstudio.microsoft.com/download/pr/1afa33fc-e800-4714-9e19-31b928ea2572/3d4f9e70b122e7f94f7c10b4c84cf6f487a44ed40f9f281fba64df0bb55bc2cd/vs_Professional.exe) |
| **Python** | 3.10.11 | [Python Downloads](https://www.python.org/downloads/) |
| **CMake** | 3.27.8 | [CMake Downloads](https://cmake.org/download/) |
| **Ninja** | 1.11.1 | [Ninja Releases](https://github.com/ninja-build/ninja/releases) |
| **Conan** | 1.60.2 | `pip install conan==1.60.2` |
| **sip** | 6.8.3 | `pip install sip==6.8.3` |

> **Important Notes:**
> - Use native PowerShell for installation, not the x86 version
> - Ensure only a single instance of VCPKG via VS Code is installed to avoid conflicts
> - See [this guide](https://www.architectryan.com/2018/03/17/add-to-the-path-on-windows-10/) for adding programs to PATH

### ⚙️ Installation Guide

1. **Install Windows 10 or higher**: Ensure you are running Windows 10 or a later version.

2. **Install Visual Studio**:
   - Download and install Visual Studio 2022 17.9.5 from above link in the table
   - During installation, select the "Desktop development with C++" workload.
   - Ensure Visual Studio is added to the system PATH.

3. **Install Python**:
   - Download and install Python 3.12 or higher from [python.org](https://www.python.org/downloads/).
   - Ensure Python is added to the system PATH during installation.

4. **Install Python Packages**:
   - Install `sip` version 6.5.1:
     ```powershell
     pip install sip==6.5.1
     ```

5. **Install CMake**:
   - Download and install CMake 3.23 or higher from [cmake.org](https://cmake.org/download/). Make sure to select the appropriate installer for your system (e.g., Windows x64 Installer).
   - Ensure CMake is added to the system PATH during installation.

6. **Install Ninja**:
   - Download Ninja 1.10 or higher from [ninja-build.org](https://github.com/ninja-build/ninja/releases).
   - Extract the downloaded zip file to a folder, for example, `C:\Ninja`.
   - Add the Ninja folder to the system PATH:
     1. Open the Start Menu, search for "Environment Variables", and select "Edit the system environment variables".
     2. In the System Properties window, click on the "Environment Variables" button.
     3. In the Environment Variables window, find the "Path" variable in the "System variables" section and select it. Click "Edit".
     4. In the Edit Environment Variable window, click "New" and add the path to the Ninja folder, e.g., `C:\Ninja`.
     5. Click "OK" to close all windows.

7. **Install Conan**:
   - **For AddiSlice 5.9 and earlier:**
     ```powershell
     pip install "conan>=1.58.0,<2.0.0"
     ```

### ✅ Verification

Ensure all installed programs are available in the system PATH by running these commands in PowerShell:
```powershell
python --version
pip show sip
cmake --version
ninja --version
conan --version
```

If any program is not available in the PATH, follow these steps to add it:

1. Open the Start Menu, search for "Environment Variables", and select "Edit the system environment variables".
2. In the System Properties window, click on the "Environment Variables" button.
3. In the Environment Variables window, find the "Path" variable in the "System variables" section and select it. Click "Edit".
4. In the Edit Environment Variable window, click "New" and add the path to the directory where the program is installed. For example:
   - For Python: `C:\Python39`
   - For CMake: `C:\Program Files\CMake\bin`
   - For Ninja: `C:\Program Files\Ninja`
5. Click "OK" to close all windows.
6. You may need to restart your computer after installation for programs to appear in your PATH.

## Building from Source

**⚠️ Important:** Perform all git clone operations in a separate workspace folder (e.g., `C:\Workspace`) to avoid cloning repositories inside the AddiSlice repository.

### Step 1: Clean Previous Builds

Remove older Conan packages and cache folders:

```powershell
conan remove "*" -s -b -f
```

Delete `.conan` folders in your user directory and system drives (C:/ or D:/).

### Step 2: Setup Conan Configuration

**Option 1: If conan-config folder doesn't exist (first time):**
```powershell
# Navigate to your workspace folder (NOT inside AddiSlice)
cd C:\Workspace  # or your preferred workspace location

# Clone and setup Conan config
git clone https://github.com/ultimaker/conan-config.git
cd conan-config
git checkout 3226488623c642b40ca7ce3f62d3f33de046d11e
cd ..
conan config install ./conan-config
conan remote remove cura-private
```

### Step 3: Build Custom CuraEngine (Optional)

If using a custom CuraEngine (see [troubleshooting guide](https://github.com/Ultimaker/CuraEngine/issues/2195) for Conan errors):

**Option 1: If CuraEngine folder doesn't exist (first time):**
```powershell
# Ensure you're in your workspace folder (NOT inside AddiSlice)
cd C:\Workspace  # or your preferred workspace location

# Clone AddiPrint CuraEngine
git clone https://github.com/FracktalWorks/CuraEngine.git
cd CuraEngine
git checkout Engine-5.9.1
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

### Step 4: Clone and Build AddiSlice

**Option 1: If AddiSlice repository doesn't exist (first time):**
```powershell
# Ensure you're in your workspace folder
cd C:\Workspace  # or your preferred workspace location

# Clone AddiSlice repository
git clone https://github.com/FracktalWorks/AddiSlice.git
cd AddiSlice
git checkout AddiSlice-5.9

# Build with custom CuraEngine:
conan install . --build=missing --update --require-override=curaengine/5.9.1@FracktalWorks/stable -o cura:devtools=True -g VirtualPythonEnv

# OR build with Ultimaker's CuraEngine:
# conan install . --build=missing --update -o cura:devtools=True -g VirtualPythonEnv
```

**Option 2: If AddiSlice repository already exists:**
```powershell
# Navigate to existing AddiSlice folder
cd C:\Workspace\AddiSlice  # or your AddiSlice location
git checkout AddiSlice-5.9
git pull

# Build with custom CuraEngine:
conan install . --build=missing --update --require-override=curaengine/5.9.1@FracktalWorks/stable -o cura:devtools=True -g VirtualPythonEnv

# OR build with Ultimaker's CuraEngine:
# conan install . --build=missing --update -o cura:devtools=True -g VirtualPythonEnv
```
### 🚀 Running AddiSlice

1. Navigate to the AddiSlice directory:
   ```powershell
   cd C:\Workspace\AddiSlice  # or your AddiSlice location
   ```

2. Set the Python environment path (replace with your actual AddiSlice directory path):
   ```powershell
   $env:PYTHONPATH = 'C:\Workspace\AddiSlice\venv\Scripts'  # or your AddiSlice location
   ```

3. Activate the virtual environment:
   ```powershell
   .\venv\Scripts\activate.ps1
   ```

4. Run AddiSlice:
   ```powershell
   python cura_app.py
   ```

## Creating Installers

Once you can successfully run AddiSlice from source, you can create MSI and EXE installers for distribution.

### 📋 Prerequisites
- **Successfully built and running AddiSlice** (completed steps above)
- **NSIS** (for .exe installers) - [Download here](https://nsis.sourceforge.io/Download)
- **WiX Toolset v3.14** (for .msi installers) - [Download here](https://wixtoolset.org/releases/)

### 🔄 Process Overview
Creating installers involves additional steps beyond building from source:
1. Install installer tools (NSIS/WiX)
2. Create `cura_inst` environment with Conan
3. Generate local environment scripts
4. Build PyInstaller executable
5. Create installer packages

### 📁 What You Get
- **`dist\AddiSlice\AddiSlice.exe`** - Standalone executable  
- **`dist\AddiSlice-{version}.exe`** - NSIS installer (if NSIS available)
- **`dist\AddiSlice-{version}.msi`** - MSI installer (if WiX available)

*Version is automatically detected from `conandata.yml` (currently 5.9.9)*

📋 **For complete step-by-step instructions, see [INSTALLER_GUIDE.md](docs/INSTALLER_GUIDE.md)**

> **Note:** Installer creation requires a different Conan build process than building from source. The installer guide provides the complete workflow including tool installation, environment setup, and installer generation.

## Version Management

### Changing Cura Version

⚠️ **Important:** Always update version numbers in both files before creating installers to ensure version consistency.

#### Step 1: Update Conan Package Version

Modify the `conandata.yml` file in the root directory to set the new version:

```yaml
version: "5.9.10"  # Update this to your new version
sources:
  "5.9.10":  # Update this key to match the version above
    url: "https://github.com/FracktalWorks/AddiSlice/archive/refs/tags/v5.9.10.tar.gz"
    strip_root: true
```

**Key Points:**
- The `version` field sets the Conan package version used in installers
- The sources key must match the version number exactly
- This version appears in installer filenames (e.g., `AddiSlice-5.9.10.exe`)

#### Step 2: Update Version for Update Checks

Modify the `latest.json` file in the `AddiSlice` folder to configure automatic update notifications:

```json
{
  "cura": {
    "Windows": {
      "major": 5,
      "minor": 9,
      "revision": 10,
      "url": "https://github.com/FracktalWorks/AddiSlice/releases"
    }
  },
  "cura-beta": {
    "Windows": {
      "major": 5,
      "minor": 9,
      "revision": 10,
      "postfix_type": "beta",
      "postfix_version": 1,
      "url": "https://github.com/FracktalWorks/AddiSlice/releases"
    }
  }
}
```

**Key Points:**
- The `major.minor.revision` should match your `conandata.yml` version
- Users will be notified when a higher version is available at the URL
- Beta versions include `postfix_type` and `postfix_version` fields

#### ✅ Version Consistency Check

Before creating installers, verify version consistency:

1. **Check conandata.yml version:** `5.9.10`
2. **Check latest.json version:** `5.9.10` (major: 5, minor: 9, revision: 10)
3. **Generated installer names:** `AddiSlice-5.9.10.exe` and `AddiSlice-5.9.10.msi`

All three should match for proper version management.

---

## Printer Profile Management


### 📚 Understanding Cura's Configuration System

AddiSlice uses Cura's container stack system for managing printer configurations. All configuration files are located in the `resources/` folder and work together to create a complete printing profile.

#### 🏗️ Container Stack Architecture

Cura organizes settings using a hierarchical **container stack** system (based on [Ultimaker's Container Stack documentation](https://github.com/Ultimaker/Cura/wiki/Container-Stacks)):

```
7. USER OVERRIDES          ← Temporary user changes in UI
6. QUALITY PROFILE         ← resources/quality/ (layer height, speed)  
5. INTENT PROFILE          ← resources/intent/ (engineering, visual, quick)
4. MATERIAL PROFILE        ← resources/materials/ (temperature, flow)
3. VARIANT PROFILE         ← resources/variants/ (nozzle size, type)
2. EXTRUDER DEFINITION     ← resources/extruders/ (extruder properties)
1. MACHINE DEFINITION      ← resources/definitions/ (printer specs)
```

#### 📁 Resource Folder Structure

| Folder | Purpose | Examples |
|--------|---------|----------|
| **`definitions/`** | Base printer specifications | `base_addiprint_printer.def.json`, `julia_2022_advanced.def.json` |
| **`extruders/`** | Extruder configurations | `base_addiprint_extruder_0.def.json` |
| **`variants/`** | Nozzle specifications | `0.4mm_nozzle.inst.cfg`, `0.6mm_volcano.inst.cfg` |
| **`materials/`** | Material properties | `PLA.xml.fdm_material`, `ABS.xml.fdm_material` |
| **`intent/`** | Print intent profiles | `engineering/`, `visual/`, `quick/` |
| **`quality/`** | Layer height & speed | `0.2mm.inst.cfg`, `0.4mm_draft.inst.cfg` |

#### ⚙️ How Settings Override Each Other

Settings flow **upward** through the stack. Higher layers override lower layers:

1. **Machine Definition** → Sets base capabilities (max temp, build volume)
2. **Extruder Definition** → Defines extruder-specific settings  
3. **Variant (Nozzle)** → Overrides for specific nozzle sizes
4. **Material** → Temperature, flow, cooling settings
5. **Intent** → Speed/quality balance (engineering vs visual)
6. **Quality** → Layer height and related speed adjustments
7. **User Overrides** → Manual changes in the UI

**Example:** A `0.6mm nozzle` variant might override the base `layer_height` from 0.2mm to 0.3mm, then a `draft quality` profile might further increase it to 0.4mm.

For detailed information, see [Ultimaker's Profiles & Settings documentation](https://github.com/Ultimaker/Cura/wiki/Profiles-&-Settings).


### 🔧 Adding New Printers

#### Step 1: Create Printer Definition
1. Create a new `.def.json` file in `resources/definitions/`
2. Base it on existing definitions (e.g., `base_addiprint_printer.def.json`)
3. Define printer-specific parameters:
   - Build volume
   - Extruder count
   - Machine-specific settings

#### Step 2: Generate Nozzle Variants
1. Use the `Variant Creator.py` script to automatically generate nozzle variants
2. Provide the path to your printer definition file
3. Specify nozzle type (regular or volcano)
4. The script creates properly configured variants in the correct folder

#### Step 3: Generate Start/End GCode (for IDEX or printers with barrel heaters)
Use the `scripts/generate_start_gcode.py` script to generate correctly formatted gcode expressions:
```powershell
# For IDEX with barrel heater (pellet extruder):
python scripts/generate_start_gcode.py --type idex --barrel --pellet --name "My Printer"

# For single extruder with barrel heater:
python scripts/generate_start_gcode.py --type single --barrel --pellet --name "My Printer"

# Write directly to definition file:
python scripts/generate_start_gcode.py --printer penrose_600_idex --write resources/definitions/penrose_600_idex.def.json
```

> **For AI Agents**: See [docs/agents.md](docs/agents.md) for comprehensive guidance on printer creation, temperature settings, gcode expression patterns, and common pitfalls.

### 🧪 Adding New Materials

#### 🚀 Quick Material Duplication
Use the `resourcesRenamerUtility.py` script for efficient material management:

1. **Rename files** (Option 1):
   - Provide path to existing material folder (e.g., `resources/intent/base_addiprint_printer/PLA`)
   - Enter old material name (e.g., "PLA")
   - Enter new material name (e.g., "TPU")

2. **Update properties** (Option 2):
   - Find and replace text within files
   - Update temperature, cooling, and other material-specific parameters

#### 📋 Complete Material Setup

For comprehensive material integration:

##### 1. Material File Creation
- Place new material XML in `resources/materials/AddiPrint/`
- Include all metadata: temperatures, cooling, properties
- Set reasonable default `speed_print` (e.g., 60 mm/s)

##### 2. Intent Profile Creation
- Create profiles in `resources/intent/base_addiprint_printer/<MaterialName>/Model <NozzleSize>/`
- Generate intents for each profile type (engineering, visual, quick) and nozzle size
- Use existing materials (ABS, Nylon, PC) as templates

##### 3. Profile Configuration
| Profile Type | Settings | Speed Configuration |
|--------------|----------|-------------------|
| **Engineering** | `material_print_temperature`, `infill_sparse_density`, `wall_thickness` | Inherit from material |
| **Visual/Quick** | Temperature adjustments + speed limits | Set max speed per nozzle (e.g., 100mm/s for 0.4mm, 80mm/s for 0.6mm) |

##### 4. Consistency Guidelines
- Follow existing material structure and naming
- Ensure speed/temperature logic matches project standards
- **TODO**: Implement flow limiting per nozzle size in Quality Settings

This process ensures new materials are fully integrated and behave as expected in AddiSlice.

### ⚙️ Custom Settings Management

#### 📍 Setting Location Rules

| Setting Type | Location | Reason |
|--------------|----------|--------|
| **Customer-facing** (used in material profiles) | `fdmprinter.def.json` | Material profiles reference base fdmprinter definitions |
| **Internal** (used by quality/intent profiles) | `base_addiprint_printer.def.json` | Inherited by all printers using this base |

#### 📝 Setting Structure Example

```json
"custom_cooling_fan_speed": {
  "label": "Custom Fan Speed",
  "description": "Custom cooling fan speed for specific materials",
  "type": "float",
  "default_value": 100,
  "unit": "%"
}
```

#### 🔧 Available Custom Settings

##### Core Custom Settings

| Setting | Location | Description | Default |
|---------|----------|-------------|---------|
| `strengthen_tree_support` | `fdmprinter.def.json` | Enables/disables tree support strengthening | - |
| `machine_max_print_speed` | `fdmprinter.def.json` (speed category) | Hard upper limit for print speed | 150 mm/s |
| `machine_visual_print_speed` | `fdmprinter.def.json` (speed category) | Recommended speed for visual quality | 60 mm/s |

##### 🏃‍♂️ Print Speed Configuration Hierarchy

1. **Materials**: Set base `speed_print` value for engineering/balanced intents
2. **Intents**: Modify speed for Visual/Quick profiles using machine speed references
3. **Quality**: Set `maximum_material_print_speed` for larger nozzles to prevent over-extrusion

> **TODO**: Implement flow limiting per nozzle size in Quality settings instead of hardcoded values in intents.

---

### 🔧 Start GCode Generator

The `scripts/generate_start_gcode.py` script generates properly formatted `machine_start_gcode` and `machine_end_gcode` values for printer definition files. It supports:

- **Single extruder** and **IDEX** printer types
- **Filament** and **pellet** extruder purge sequences
- **Barrel heater** temperature commands (M104 H/M109 H)
- All 5 IDEX print modes (Single 1, Single 2, Dual, Mirror, Duplication)
- Python expression validation (`ast.parse`)
- Direct write to `.def.json` files

#### Usage Examples

```powershell
# Show available presets and options:
python scripts/generate_start_gcode.py --help

# Generate for a known printer preset:
python scripts/generate_start_gcode.py --printer penrose_600_idex

# Custom IDEX with barrel heater:
python scripts/generate_start_gcode.py --type idex --barrel --pellet --name "My IDEX Printer"

# Write directly to definition file:
python scripts/generate_start_gcode.py --printer penrose_600_idex \
    --write resources/definitions/penrose_600_idex.def.json

# Validate existing definition:
python scripts/generate_start_gcode.py --validate-only \
    --write resources/definitions/penrose_600_idex.def.json
```

#### Available Presets

| Preset | Type | Barrel | Extruder | Description |
|--------|------|--------|----------|-------------|
| `penrose_600_idex` | IDEX | ✅ | Pellet | Penrose 600 IDEX pellet extruder |
| `penrose_600` | Single | ✅ | Pellet | Penrose 600 pellet extruder |
| `base_idex_filament` | IDEX | ❌ | Filament | Generic IDEX filament printer |
| `base_single_filament` | Single | ❌ | Filament | Generic single filament printer |

To add new presets, edit the `PRESETS` dictionary in `scripts/generate_start_gcode.py`.

