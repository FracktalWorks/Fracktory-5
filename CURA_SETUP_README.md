# Cura Windows Development Setup

This repository contains automated scripts to set up a complete Cura development environment on Windows, based on the official [Running Cura from Source](https://github.com/Ultimaker/Cura/wiki/Running-Cura-from-Source) documentation.

## Quick Start

1. **Run as Administrator** (recommended):
   ```powershell
   # Download and run the setup script
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   .\setup-cura-windows.ps1
   ```

2. **Setup Cura repository** (after the first script completes):
   ```powershell
   .\setup-cura-repository.ps1
   ```

3. **Run Cura**:
   ```powershell
   .\run-cura.ps1
   ```

## What Gets Installed

### System Requirements (setup-cura-windows.ps1)
- **Chocolatey**: Package manager for Windows
- **Git**: Version control system  
- **Python 3.12**: Required Python version
- **Visual Studio Build Tools 2022**: MSVC compiler and Windows SDK
- **CMake 3.23+**: Build system generator
- **Ninja 1.10+**: Fast build system
- **Conan 2.7.0**: C++ package manager

### Development Environment (setup-cura-repository.ps1)
- Clones the official Cura repository
- Sets up Python virtual environments
- Installs all Cura dependencies via Conan
- Creates convenience scripts for running Cura

## Script Options

### setup-cura-windows.ps1 Parameters

```powershell
.\setup-cura-windows.ps1 [options]

Options:
  -SkipVS          Skip Visual Studio Build Tools installation
  -SkipPython      Skip Python installation 
  -Force           Force reinstallation of components
  -InstallPath     Custom installation path (default: C:\Cura-Dev)
```

**Examples:**
```powershell
# Basic installation
.\setup-cura-windows.ps1

# Skip Visual Studio if already installed
.\setup-cura-windows.ps1 -SkipVS

# Custom installation location
.\setup-cura-windows.ps1 -InstallPath "D:\Development\Cura"

# Force reinstall everything
.\setup-cura-windows.ps1 -Force
```

### setup-cura-repository.ps1 Parameters

```powershell
.\setup-cura-repository.ps1 [options]

Options:
  -ProjectPath     Where to clone Cura (default: C:\Cura-Dev)
  -VenvPath        Virtual environment path (default: C:\Cura-Dev\cura_venv)
  -Repository      Git repository URL (default: official Cura repo)
  -Force           Force re-clone of repository
  -DevTools        Install additional development tools (pytest, etc.)
```

**Examples:**
```powershell
# Basic repository setup
.\setup-cura-repository.ps1

# Include development tools
.\setup-cura-repository.ps1 -DevTools

# Custom paths
.\setup-cura-repository.ps1 -ProjectPath "D:\Development" -VenvPath "D:\Development\venv"

# Force fresh clone
.\setup-cura-repository.ps1 -Force
```

## Manual Installation Steps

If you prefer to install manually or need to troubleshoot:

### 1. Install System Dependencies

```powershell
# Install Chocolatey
Set-ExecutionPolicy Bypass -Scope Process -Force
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install required tools
choco install git python312 cmake ninja visualstudio2022buildtools -y
```

### 2. Setup Python Environment

```powershell
# Create virtual environment
python -m venv cura_venv
cura_venv\Scripts\activate.ps1

# Install Conan
pip install conan==2.7.0
conan config install https://github.com/ultimaker/conan-config.git
conan profile detect --force
```

### 3. Clone and Build Cura

```powershell
# Clone repository
git clone https://github.com/Ultimaker/Cura.git
cd Cura

# Install dependencies
conan install . --build=missing --update -g VirtualPythonEnv

# Activate Cura environment and run
build\generators\virtual_python_env.ps1
python cura_app.py
```

## Troubleshooting

### Common Issues

**"Execution Policy" errors:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**"Access Denied" during installation:**
- Run PowerShell as Administrator
- Disable antivirus temporarily during installation

**Visual Studio Build Tools not found:**
```powershell
# Manual installation
choco install visualstudio2022buildtools --package-parameters "--add Microsoft.VisualStudio.Workload.VCTools"
```

**Conan fails with system requirements error:**
- Ensure all system dependencies are installed first
- Run the scripts as Administrator
- Check that Visual Studio Build Tools are properly installed

**Python version issues:**
```powershell
# Check Python version
python --version

# Should show Python 3.12.x
# If not, reinstall Python 3.12
choco install python312 -y --force
```

### Long Paths on Windows

If you encounter path length issues:
```powershell
# Enable long paths (requires Admin)
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

### Disk Space

The complete setup requires approximately:
- **System tools**: ~3-4 GB
- **Conan dependencies**: ~2-3 GB  
- **Cura source**: ~500 MB
- **Build artifacts**: ~1-2 GB

**Total**: ~7-10 GB free space recommended

## Development Workflow

Once setup is complete:

1. **Daily development**:
   ```powershell
   cd C:\Cura-Dev\Cura
   build\generators\virtual_python_env.ps1
   python cura_app.py
   ```

2. **Running tests** (if -DevTools was used):
   ```powershell
   cd C:\Cura-Dev\Cura  
   build\generators\virtual_python_env.ps1
   pytest tests/
   ```

3. **Updating dependencies**:
   ```powershell
   cd C:\Cura-Dev\Cura
   cura_venv\Scripts\activate.ps1
   conan install . --build=missing --update -g VirtualPythonEnv
   ```

4. **Updating Cura source**:
   ```powershell
   cd C:\Cura-Dev\Cura
   git pull origin main
   # Re-run conan install if dependencies changed
   ```

## File Structure After Installation

```
C:\Cura-Dev\
├── cura_venv\              # Initial Python virtual environment
├── Cura\                   # Cura source code
│   ├── build\generators\   # Conan-generated build files
│   │   ├── cura_venv\     # Cura runtime environment 
│   │   └── virtual_python_env.ps1
│   ├── cura_app.py        # Main Cura application
│   ├── run-cura.ps1       # Convenience script
│   └── ...
```

## Environment Variables

The scripts automatically handle PATH updates, but you may need to:

1. **Restart your terminal** after running setup-cura-windows.ps1
2. **Refresh environment variables**:
   ```powershell
   $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
   ```

## Getting Help

- **Cura Wiki**: https://github.com/Ultimaker/Cura/wiki
- **Cura Issues**: https://github.com/Ultimaker/Cura/issues
- **Conan Documentation**: https://docs.conan.io/

## System Requirements Summary

- **OS**: Windows 10 or higher
- **RAM**: 8 GB minimum, 16 GB recommended
- **Storage**: 10 GB free space
- **Network**: Internet connection for downloading dependencies
- **Privileges**: Administrator access recommended