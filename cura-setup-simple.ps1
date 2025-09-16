# Cura Windows Setup Script - Working Version
param(
    [switch]$SkipVS,
    [switch]$SkipPython,
    [switch]$Force,
    [string]$InstallPath = "C:\Cura-Dev"
)

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Write-Host "=== Cura Windows Development Environment Setup ===" -ForegroundColor Cyan

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-Command {
    param([string]$Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Get-PythonVersion {
    try {
        $pythonOutput = & python --version 2>&1
        if ($pythonOutput -match "Python (\d+\.\d+\.\d+)") {
            return [Version]$matches[1]
        }
    } catch {
        return $null
    }
    return $null
}

if (-not (Test-Administrator)) {
    Write-Warning "This script should be run as Administrator for best results."
    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -notmatch '^[Yy]') {
        exit 1
    }
}

if (-not (Test-Path $InstallPath)) {
    New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
}

Write-Host "`n=== Installing Chocolatey ===" -ForegroundColor Cyan
if (-not (Test-Command "choco")) {
    Write-Host "Installing Chocolatey..." -ForegroundColor Green
    Set-ExecutionPolicy Bypass -Scope Process -Force
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
} else {
    Write-Host "Chocolatey already installed." -ForegroundColor Yellow
}

Write-Host "`n=== Installing Git ===" -ForegroundColor Cyan
if (-not (Test-Command "git")) {
    Write-Host "Installing Git..." -ForegroundColor Green
    choco install git -y
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
} else {
    Write-Host "Git already installed." -ForegroundColor Yellow
}

Write-Host "`n=== Installing Python 3.12 ===" -ForegroundColor Cyan
$pythonVersion = Get-PythonVersion
$needsPython = $null -eq $pythonVersion -or $pythonVersion.Major -lt 3 -or ($pythonVersion.Major -eq 3 -and $pythonVersion.Minor -lt 12)
if ($needsPython -and (-not $SkipPython)) {
    Write-Host "Installing Python 3.12..." -ForegroundColor Green
    choco install python312 -y
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
} else {
    Write-Host "Python requirements satisfied." -ForegroundColor Yellow
}

if (-not $SkipVS) {
    Write-Host "`n=== Installing Visual Studio Build Tools ===" -ForegroundColor Cyan
    $vsInstallerPath = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vs_installer.exe"
    if (-not (Test-Path $vsInstallerPath)) {
        Write-Host "Installing Visual Studio Build Tools 2022..." -ForegroundColor Green
        choco install visualstudio2022buildtools --package-parameters "--add Microsoft.VisualStudio.Workload.VCTools" -y
    } else {
        Write-Host "Visual Studio Build Tools already installed." -ForegroundColor Yellow
    }
}

Write-Host "`n=== Installing CMake ===" -ForegroundColor Cyan
if (-not (Test-Command "cmake")) {
    Write-Host "Installing CMake..." -ForegroundColor Green
    choco install cmake -y
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
} else {
    Write-Host "CMake already installed." -ForegroundColor Yellow
}

Write-Host "`n=== Installing Ninja ===" -ForegroundColor Cyan
if (-not (Test-Command "ninja")) {
    Write-Host "Installing Ninja..." -ForegroundColor Green
    choco install ninja -y
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
} else {
    Write-Host "Ninja already installed." -ForegroundColor Yellow
}

Write-Host "`n=== Setting up Python Virtual Environment ===" -ForegroundColor Cyan
$venvPath = Join-Path $InstallPath "cura_venv"
if (-not (Test-Path $venvPath) -or $Force) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Green
    & python -m venv $venvPath
} else {
    Write-Host "Virtual environment already exists." -ForegroundColor Yellow
}

$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    Write-Host "Activating virtual environment..." -ForegroundColor Green
    & $activateScript
} else {
    Write-Error "Failed to find activation script"
    exit 1
}

Write-Host "`n=== Installing Conan ===" -ForegroundColor Cyan
& pip install conan==2.7.0
& conan config install https://github.com/ultimaker/conan-config.git
& conan profile detect --force

Write-Host "`n=== Installation Complete ===" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. git clone https://github.com/Ultimaker/Cura.git" -ForegroundColor White
Write-Host "2. cd Cura" -ForegroundColor White
Write-Host "3. $venvPath\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "4. conan install . --build=missing --update -g VirtualPythonEnv" -ForegroundColor White
Write-Host "5. build\generators\virtual_python_env.ps1" -ForegroundColor White
Write-Host "6. python cura_app.py" -ForegroundColor White