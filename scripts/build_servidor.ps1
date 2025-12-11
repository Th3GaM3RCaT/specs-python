# Script para compilar el servidor de Specs con PyInstaller
# Uso: .\scripts\build_servidor.ps1

Write-Host "🔨 Compilando Servidor de Specs..." -ForegroundColor Cyan
Write-Host ""

# Verificar que estamos en la raíz del proyecto
if (!(Test-Path "src/mainServidor.py")) {
    Write-Host "❌ Error: Ejecuta este script desde la raíz del proyecto" -ForegroundColor Red
    Write-Host "   Ejemplo: .\scripts\build_servidor.ps1" -ForegroundColor Yellow
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
if (Test-Path "dist/SpecsServidor") {
    Write-Host "🧹 Eliminando build anterior..." -ForegroundColor Yellow
    Remove-Item "dist/SpecsServidor" -Recurse -Force
}

if (Test-Path "build") {
    Remove-Item "build" -Recurse -Force -ErrorAction SilentlyContinue
}

if (Test-Path "SpecsServidor.spec") {
    Remove-Item "SpecsServidor.spec" -Force -ErrorAction SilentlyContinue
}

# Compilar con PyInstaller
Write-Host "⚙️  Ejecutando PyInstaller..." -ForegroundColor Cyan

$pyinstallerArgs = @(
    "--onedir",
    "--noconsole",
    "--name", "SpecsNet - Servidor",
    "--add-data", "src/ui/Combinear.qss;ui",
    "--paths=src",
    "src/mainServidor.py"
)

# Agregar security_config si existe
if (Test-Path "config/security_config.py") {
    Write-Host "✓ Incluyendo security_config.py" -ForegroundColor Green
    $pyinstallerArgs += "--add-data"
    $pyinstallerArgs += "config/security_config.py;config"
}

# Agregar .env si existe
if (Test-Path ".env") {
    Write-Host "✓ Incluyendo .env" -ForegroundColor Green
    $pyinstallerArgs += "--add-data"
    $pyinstallerArgs += ".env;."
}

pyinstaller @pyinstallerArgs

# Verificar resultado
if (Test-Path "dist/SpecsNet - Servidor/SpecsNet - Servidor.exe") {
    $fileSize = (Get-Item "dist/SpecsNet - Servidor/SpecsNet - Servidor.exe").Length / 1MB
    $folderSize = (Get-ChildItem "dist/SpecsNet - Servidor" -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Host ""
    Write-Host "✅ Compilación exitosa!" -ForegroundColor Green
    Write-Host "   Ejecutable: dist/SpecsNet - Servidor/SpecsNet - Servidor.exe" -ForegroundColor Cyan
    Write-Host "   Tamaño exe: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Cyan
    Write-Host "   Tamaño total: $([math]::Round($folderSize, 2)) MB" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "🚀 Para ejecutar:" -ForegroundColor Yellow
    Write-Host "   .\dist\SpecsNet - Servidor\SpecsNet - Servidor.exe" -ForegroundColor White
    Write-Host ""
    Write-Host "💡 Tip: Para distribuir, comprime toda la carpeta dist/SpecsNet - Servidor/" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "❌ Error en la compilación" -ForegroundColor Red
    Write-Host "   Revisa los logs arriba para más detalles" -ForegroundColor Yellow
    Throw
}
