# CI/CD Setup Guide

This guide explains how to set up and run the GitHub Actions workflow for automated Fracktory installer creation using local runners.

## Overview

The Fracktory project uses GitHub Actions with self-hosted Windows runners to create MSI and EXE installers. This approach provides:
- **Full control** over the build environment
- **Better performance** than hosted runners
- **Access to licensed tools** (NSIS, WiX Toolset)
- **Consistent build environment** matching local development

## Prerequisites

### System Requirements
- **Windows 10/11** or **Windows Server 2019/2022**
- **PowerShell 5.1** or higher
- **Administrator access** for runner installation
- **Visual Studio Build Tools** or Visual Studio 2022
- **Python 3.10+** with pip
- **Git** for Windows
- **CMake 3.23+** and **Ninja 1.10+**

### Required Tools
- **NSIS** - [Download from nsis.sourceforge.io](https://nsis.sourceforge.io/Download)
- **WiX Toolset v3.14** - [Download from wixtoolset.org](https://wixtoolset.org/releases/)
- **Conan 1.65.0** - Installed via pip during setup

## Setting Up GitHub Self-Hosted Runner

### Step 1: Create Runner on GitHub

1. **Navigate to Repository Settings:**
   - Go to: https://github.com/FracktalWorks/Fracktory-5/settings/actions/runners

2. **Add New Runner:**
   - Click **"New self-hosted runner"**
   - Select **Windows** as the operating system
   - Choose **x64** architecture

3. **Copy Runner Configuration Commands:**
   GitHub will provide commands similar to:
   ```powershell
   # Download
   mkdir actions-runner; cd actions-runner
   Invoke-WebRequest -Uri https://github.com/actions/runner/releases/download/v2.x.x/actions-runner-win-x64-2.x.x.zip -OutFile actions-runner-win-x64-2.x.x.zip
   Add-Type -AssemblyName System.IO.Compression.FileSystem ; [System.IO.Compression.ZipFile]::ExtractToDirectory("$PWD/actions-runner-win-x64-2.x.x.zip", "$PWD")
   ```

### Step 2: Configure Runner on Your Machine

1. **Run Configuration Commands:**
   Execute the download and extraction commands from GitHub in PowerShell as Administrator.

2. **Configure the Runner:**
   ```powershell
   ./config.cmd --url https://github.com/FracktalWorks/Fracktory-5 --token YOUR_TOKEN_HERE
   ```

3. **Runner Configuration Settings:**
   - **Runner group:** Default
   - **Runner name:** `windows-fracktory-builder` (or your preferred name)
   - **Labels:** `self-hosted,Windows,X64` (default)
   - **Work folder:** Use default (`_work`)

### Step 3: Choose Runner Execution Method

You have two options for running the GitHub Actions runner:

#### Option A: Run as Windows Service (Recommended for Production)

1. **Install Service (Run as Administrator):**
   ```powershell
   ./svc.sh install
   ```

2. **Start Service:**
   ```powershell
   ./svc.sh start
   ```

3. **Verify Service Status:**
   ```powershell
   ./svc.sh status
   ```

**Benefits:**
- Runs automatically on system startup
- Runs in background without user interaction
- Survives user logouts and reboots

#### Option B: Run Manually (Good for Testing/Development)

1. **Start Runner Manually:**
   ```powershell
   # Navigate to actions-runner directory
   cd C:\path\to\actions-runner
   ./run.cmd
   ```

2. **Keep Terminal Open:**
   - Runner runs in foreground
   - Shows live log output
   - Stops when terminal is closed

**Benefits:**
- See real-time logs and output
- Easy to start/stop for testing
- No service installation required
- Good for debugging runner issues

### Step 4: Verify Runner Registration

1. **Check GitHub Settings:**
   - Go back to: https://github.com/FracktalWorks/Fracktory-5/settings/actions/runners
   - Your runner should appear with a green dot (online status)

2. **Runner Labels:**
   Ensure your runner has these labels:
   - `self-hosted`
   - `Windows`
   - `X64`

## Running the GitHub Actions Workflow

### Step 1: Trigger Workflow

1. **Navigate to Actions Tab:**
   - Go to: https://github.com/FracktalWorks/Fracktory-5/actions

2. **Select Workflow:**
   - Click **"Fracktory Windows Installer Local Runner"**

3. **Run Workflow:**
   - Click **"Run workflow"** button
   - Fill in the parameters:

### Step 2: Workflow Parameters

| Parameter | Description | Default | Notes |
|-----------|-------------|---------|-------|
| **version** | Version of the application | `5.9.9` | Must match your conandata.yml |
| **installer_name** | Name of the .exe and .msi | `Fracktory_setup` | Base filename for installers |
| **app_name** | Application name in installer | `Fracktory` | Display name in Windows |
| **conan_args** | Additional Conan arguments | `''` | For advanced users |
| **enterprise** | Build as Enterprise edition | `false` | Usually keep false |
| **staging** | Use staging API | `false` | Usually keep false |
| **architecture** | Target architecture | `X64` | Keep as X64 |
| **operating_system** | OS for runner selection | `windows-2022` | Matches runner OS |
| **conan_internal** | Internal Conan settings | `false` | Usually keep false |

### Step 3: Monitor Workflow Execution

1. **Watch Progress:**
   - Click on the running workflow to see live progress
   - Monitor each step for errors

2. **Key Steps to Watch:**
   - ✅ **Checkout repo** - Repository code download
   - ✅ **Install Conan and dependencies** - Package manager setup
   - ✅ **Clone and setup CuraEngine** - Engine dependency build
   - ✅ **Create the Packages** - Conan package creation
   - ✅ **Create the Cura dist** - PyInstaller executable creation
   - ✅ **Build EXE Installer (NSIS)** - Windows installer creation
   - ✅ **Build MSI Installer** - MSI package creation

3. **Troubleshoot Failures:**
   - Click on failed steps to see error details
   - Check runner system has all required tools installed
   - Verify runner has sufficient disk space (10GB+ recommended)

### Step 4: Download Artifacts

1. **Locate Artifacts:**
   - Scroll to bottom of workflow run page
   - Look for **"Artifacts"** section

2. **Available Downloads:**
   - **`Fracktory-Installer-EXE-{version}`** - Contains the NSIS .exe installer
   - **`Fracktory-Installer-MSI-{version}`** - Contains the MSI installer
   - **`windows-run-info`** - Contains build information

3. **Download and Test:**
   - Download both installer artifacts
   - Test installation on clean Windows systems
   - Verify installers work correctly

## Workflow Process Details

### Environment Setup
The workflow performs these key setup steps:

1. **System Preparation:**
   ```yaml
   - Python version verification
   - Pip upgrade
   - PowerShell PATH configuration
   ```

2. **Conan Configuration:**
   ```yaml
   - Install Conan 1.65.0
   - Clone Ultimaker conan-config
   - Configure Conan with FracktalWorks settings
   ```

3. **CuraEngine Build:**
   ```yaml
   - Clone FracktalWorks/CuraEngine
   - Build custom CuraEngine package
   - Register with Conan
   ```

### Package Creation
The workflow creates packages using:

1. **Conan Package Creation:**
   ```powershell
   conan create . local/test --build=missing --update
   conan install cura/5.9.9@local/test --require-override=curaengine/5.9.9@FracktalWorks/stable
   ```

2. **Environment Activation:**
   ```powershell
   .\cura_inst\Scripts\activate_github_actions_env.ps1
   .\cura_inst\Scripts\activate_github_actions_version_env.ps1
   ```

### Installer Generation
The workflow creates installers using:

1. **PyInstaller Executable:**
   ```powershell
   pyinstaller ./cura_inst/Fracktory.spec
   ```

2. **NSIS EXE Installer:**
   ```powershell
   python cura_inst\packaging\NSIS\create_windows_installer.py cura_inst dist "Fracktory-5.9.9.exe"
   ```

3. **WiX MSI Installer:**
   ```powershell
   python cura_inst\packaging\msi\create_windows_msi.py cura_inst dist\Fracktory "Fracktory-5.9.9.msi" "Fracktory"
   ```

## Troubleshooting

### Common Runner Issues

**Runner Offline:**
- Check Windows Service is running: `Services.msc` → "GitHub Actions Runner"
- Restart service if needed: `./svc.sh restart`
- Verify network connectivity to GitHub

**Build Failures:**
- Ensure all prerequisite tools are installed
- Check available disk space (>10GB recommended)
- Verify Visual Studio Build Tools are properly installed

**Permission Issues:**
- Run runner installation as Administrator
- Ensure runner service account has necessary permissions
- Check file system permissions in work directory

### Workflow Debugging

**Conan Errors:**
- Clear Conan cache: `conan remove "*" -s -b -f`
- Check internet connectivity for package downloads
- Verify Conan configuration matches local setup

**PyInstaller Issues:**
- Check Python environment setup
- Verify all dependencies are properly installed
- Review PyInstaller spec file for missing modules

**Installer Creation Failures:**
- Ensure NSIS and WiX are installed and in PATH
- Check file permissions in output directories
- Verify version format compatibility

### Performance Optimization

**Speed Up Builds:**
- Use SSD storage for runner work directory
- Increase runner machine RAM (16GB+ recommended)
- Cache Conan downloads between builds
- Use local Conan package cache

**Resource Management:**
- Monitor runner machine resource usage
- Set up multiple runners for parallel builds
- Schedule builds during off-peak hours

## Security Considerations

### Runner Security
- **Isolate runner machine** from production networks
- **Regular security updates** for Windows and tools
- **Monitor runner activity** for suspicious operations
- **Limit runner permissions** to minimum required

### Repository Access
- **Use dedicated service account** for runner registration
- **Rotate runner tokens** regularly
- **Monitor repository access logs** for runner activity
- **Restrict workflow triggers** to authorized users

### Artifact Security
- **Scan generated installers** for malware before distribution
- **Sign installers** with code signing certificates (if available)
- **Secure artifact storage** and download processes
- **Version control** all installer creation scripts

## Maintenance

### Regular Tasks
- **Update runner software** when new versions are available
- **Clean work directories** periodically to free disk space
- **Monitor system performance** and resource usage
- **Update build tools** (NSIS, WiX, Python packages)

### Monitoring
- **Check runner status** daily in GitHub Settings
- **Review workflow run history** for patterns or issues
- **Monitor system logs** for runner service issues
- **Track artifact download statistics**

---

## Quick Reference Commands

### Runner Management
```powershell
# Check service status
./svc.sh status

# Restart service
./svc.sh stop
./svc.sh start

# Remove runner (from runner directory)
./config.cmd remove --token YOUR_TOKEN
```

### Manual Testing
```powershell
# Test runner connectivity
./run.cmd

# Clean work directory
Remove-Item -Recurse -Force _work\*
```

### Workflow Trigger
1. Go to: https://github.com/FracktalWorks/Fracktory-5/actions
2. Select "Fracktory Windows Installer Local Runner"
3. Click "Run workflow"
4. Fill parameters and click "Run workflow"

This setup ensures reliable, automated installer creation for the Fracktory project using GitHub Actions and self-hosted runners.