# Script para compilar el cliente de Specs con PyInstaller
# Uso: .\scripts\build_cliente.ps1

Write-Host "🔨 Compilando Cliente de Specs..." -ForegroundColor Cyan
Write-Host ""

# Verificar que estamos en la raíz del proyecto
if (!(Test-Path "src/specs.py")) {
    Write-Host "❌ Error: Ejecuta este script desde la raíz del proyecto" -ForegroundColor Red
    Write-Host "   Ejemplo: .\scripts\build_cliente.ps1" -ForegroundColor Yellow
    Throw
}

# Verificar que PyInstaller está instalado
try {
    $null = Get-Command pyinstaller -ErrorAction Stop
} catch {
    Write-Host "❌ PyInstaller no está instalado" -ForegroundColor Red
    Write-Host "   Instala con: pip install pyinstaller" -ForegroundColor Yellow
    Throw
}

# Limpiar builds anteriores
if (Test-Path "dist/SpecsCliente") {
    Write-Host "🧹 Eliminando build anterior..." -ForegroundColor Yellow
    Remove-Item "dist/SpecsCliente" -Recurse -Force
}

if (Test-Path "build") {
    Remove-Item "build" -Recurse -Force -ErrorAction SilentlyContinue
}

if (Test-Path "SpecsCliente.spec") {
    Remove-Item "SpecsCliente.spec" -Force -ErrorAction SilentlyContinue
}

# Compilar con PyInstaller
Write-Host "⚙️  Ejecutando PyInstaller..." -ForegroundColor Cyan

$pyinstallerArgs = @(
    "--onedir",
    "--noconsole",
    "--name", "SpecsNet - Cliente",
    "--add-data", "src/ui/*.ui;ui",
    "--hidden-import=wmi",
    "--hidden-import=psutil",
    "--hidden-import=getmac",
    "--hidden-import=windows_tools.installed_software",
    "--hidden-import=PySide6",
    "--hidden-import=PySide6.QtCore",
    "--hidden-import=PySide6.QtGui",
    "--hidden-import=PySide6.QtWidgets",
    "--paths=src",
    "src/specs.py"
)

# Agregar security_config si existe
if (Test-Path "config/security_config.py") {
    Write-Host "✓ Incluyendo security_config.py" -ForegroundColor Green
    $pyinstallerArgs += "--add-data"
    $pyinstallerArgs += "config/security_config.py;config"
}

# Agregar server_config.json si existe
if (Test-Path "config/server_config.json") {
    Write-Host "✓ Incluyendo server_config.json" -ForegroundColor Green
    $pyinstallerArgs += "--add-data"
    $pyinstallerArgs += "config/server_config.json;config"
}

# Agregar .env si existe
if (Test-Path ".env") {
    Write-Host "✓ Incluyendo .env" -ForegroundColor Green
    $pyinstallerArgs += "--add-data"
    $pyinstallerArgs += ".env;."
}

pyinstaller @pyinstallerArgs

# Verificar resultado
if (Test-Path "dist/SpecsNet - Cliente/SpecsNet - Cliente.exe") {
    $fileSize = (Get-Item "dist/SpecsNet - Cliente/SpecsNet - Cliente.exe").Length / 1MB
    $folderSize = (Get-ChildItem "dist/SpecsNet - Cliente" -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Host ""
    Write-Host "✅ Compilación exitosa!" -ForegroundColor Green
    Write-Host "   Ejecutable: dist/SpecsNet - Cliente/SpecsNet - Cliente.exe" -ForegroundColor Cyan
    Write-Host "   Tamaño exe: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Cyan
    Write-Host "   Tamaño total: $([math]::Round($folderSize, 2)) MB" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "🚀 Para ejecutar:" -ForegroundColor Yellow
    Write-Host "   GUI mode:   .\dist\SpecsNet - Cliente\SpecsCliente.exe" -ForegroundColor White
    Write-Host "   Tarea mode: .\dist\SpecsNet - Cliente\SpecsNet - Cliente.exe --tarea" -ForegroundColor White
    Write-Host ""
    Write-Host "💡 Tip: Para distribuir, comprime toda la carpeta dist/SpecsNet - Cliente/" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "❌ Error en la compilación" -ForegroundColor Red
    Write-Host "   Revisa los logs arriba para más detalles" -ForegroundColor Yellow
    Throw
}
