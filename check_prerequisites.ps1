# Check Prerequisites for Fracktory Installers
Write-Host "=== Fracktory Installer Prerequisites Checker ===" -ForegroundColor Cyan

$allGood = $true

# Check if source environment works first
Write-Host "`nChecking Source Environment..." -ForegroundColor Yellow

if (Test-Path "cura_inst\Scripts\python.exe") {
    Write-Host "   Virtual environment found" -ForegroundColor Green
    
    # Test if Fracktory can be imported
    & ".\cura_inst\Scripts\python.exe" -c "import cura" 2>$null | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   Source environment is working" -ForegroundColor Green
    } else {
        Write-Host "   Cannot import Cura (run python cura_app.py first)" -ForegroundColor Red
        $allGood = $false
    }
} else {
    Write-Host "   Virtual environment not found (follow README first)" -ForegroundColor Red
    $allGood = $false
}

# Check PyInstaller
Write-Host "`nChecking PyInstaller..." -ForegroundColor Yellow
if (Test-Path ".\cura_inst\Scripts\pyinstaller.exe") {
    Write-Host "   PyInstaller found" -ForegroundColor Green
} else {
    Write-Host "   PyInstaller NOT FOUND (REQUIRED)" -ForegroundColor Red
    Write-Host "    Install hint: Run .\cura_inst\Scripts\pip install pyinstaller" -ForegroundColor Yellow
    $allGood = $false
}

# Check NSIS
Write-Host "`nChecking NSIS..." -ForegroundColor Yellow
if (Test-Path "C:\Program Files (x86)\NSIS\makensis.exe") {
    Write-Host "   NSIS found" -ForegroundColor Green
} else {
    Write-Host "   NSIS not found (optional)" -ForegroundColor Yellow
    Write-Host "    Install hint: Download from https://nsis.sourceforge.io" -ForegroundColor Yellow
}

# Check WiX Toolset
Write-Host "`nChecking WiX Toolset..." -ForegroundColor Yellow
if (Test-Path "C:\Program Files (x86)\WiX Toolset v3.14\bin\candle.exe") {
    Write-Host "   WiX Toolset found" -ForegroundColor Green
} else {
    Write-Host "   WiX Toolset not found (optional)" -ForegroundColor Yellow
    Write-Host "    Install hint: Download WiX Toolset v3.14 from https://wixtoolset.org" -ForegroundColor Yellow
}

Write-Host "`n===================================================" -ForegroundColor Cyan

if ($allGood) {
    Write-Host " All prerequisites are ready!" -ForegroundColor Green
    Write-Host "`nYou can now create installers:" -ForegroundColor Cyan
    Write-Host "  .\create_installers.ps1" -ForegroundColor White
    Write-Host "  .\create_installers.ps1 -InstallAfterBuild" -ForegroundColor White
} else {
    Write-Host " Prerequisites missing!" -ForegroundColor Red
    Write-Host "`nSteps to fix:" -ForegroundColor Yellow
    Write-Host "  1. Follow README.md to get source working first" -ForegroundColor White
    Write-Host "  2. Install PyInstaller: .\cura_inst\Scripts\pip install pyinstaller" -ForegroundColor White
    Write-Host "  3. Install NSIS and/or WiX for installer creation" -ForegroundColor White
}
