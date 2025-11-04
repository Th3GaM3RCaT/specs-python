# Script para compilar el servidor de Specs con PyInstaller
# Uso: .\scripts\build_servidor.ps1

Write-Host "🔨 Compilando Servidor de Specs..." -ForegroundColor Cyan
Write-Host ""

# Verificar que estamos en la raíz del proyecto
if (!(Test-Path "src/servidor.py")) {
    Write-Host "❌ Error: Ejecuta este script desde la raíz del proyecto" -ForegroundColor Red
    Write-Host "   Ejemplo: .\scripts\build_servidor.ps1" -ForegroundColor Yellow
    exit 1
}

# Verificar que PyInstaller está instalado
try {
    $null = Get-Command pyinstaller -ErrorAction Stop
} catch {
    Write-Host "❌ PyInstaller no está instalado" -ForegroundColor Red
    Write-Host "   Instala con: pip install pyinstaller" -ForegroundColor Yellow
    exit 1
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
    "--name", "SpecsServidor",
    "--add-data", "src/sql/statement/*.sql;sql/statement",
    "--add-data", "src/ui/*.ui;ui",
    "--hidden-import=wmi",
    "--hidden-import=psutil",
    "--paths=src",
    "src/servidor.py"
)

# Agregar security_config si existe
if (Test-Path "config/security_config.py") {
    Write-Host "✓ Incluyendo security_config.py" -ForegroundColor Green
    $pyinstallerArgs += "--add-data"
    $pyinstallerArgs += "config/security_config.py;config"
}

pyinstaller @pyinstallerArgs

# Verificar resultado
if (Test-Path "dist/SpecsServidor/SpecsServidor.exe") {
    $fileSize = (Get-Item "dist/SpecsServidor/SpecsServidor.exe").Length / 1MB
    $folderSize = (Get-ChildItem "dist/SpecsServidor" -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Host ""
    Write-Host "✅ Compilación exitosa!" -ForegroundColor Green
    Write-Host "   Ejecutable: dist/SpecsServidor/SpecsServidor.exe" -ForegroundColor Cyan
    Write-Host "   Tamaño exe: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Cyan
    Write-Host "   Tamaño total: $([math]::Round($folderSize, 2)) MB" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "🚀 Para ejecutar:" -ForegroundColor Yellow
    Write-Host "   .\dist\SpecsServidor\SpecsServidor.exe" -ForegroundColor White
    Write-Host ""
    Write-Host "💡 Tip: Para distribuir, comprime toda la carpeta dist/SpecsServidor/" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "❌ Error en la compilación" -ForegroundColor Red
    Write-Host "   Revisa los logs arriba para más detalles" -ForegroundColor Yellow
    exit 1
}
