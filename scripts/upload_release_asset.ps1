# Script para subir asset a GitHub Release usando API REST
# Uso: .\upload_release_asset.ps1 -Tag "v1.0.0" -AssetPath "dist\SpecsNet - Cliente.zip"

param(
    [Parameter(Mandatory=$true)]
    [string]$Tag,
    
    [Parameter(Mandatory=$true)]
    [string]$AssetPath,
    
    [string]$Owner = "Th3GaM3RCaT",
    [string]$Repo = "SpecsNet"
)

# Verificar que el archivo existe
if (-not (Test-Path $AssetPath)) {
    Write-Host "[ERROR] Archivo no encontrado: $AssetPath" -ForegroundColor Red
    Throw
}

$file = Get-Item $AssetPath
$fileName = $file.Name
$fileSize = [math]::Round($file.Length/1MB, 2)

Write-Host "=" * 70
Write-Host "SUBIR ASSET A GITHUB RELEASE" -ForegroundColor Cyan
Write-Host "=" * 70
Write-Host "Repositorio: $Owner/$Repo"
Write-Host "Tag:         $Tag"
Write-Host "Archivo:     $fileName"
Write-Host "Tamano:      $fileSize MB"
Write-Host ""

# Solicitar token de acceso personal
Write-Host "Necesitas un Personal Access Token (PAT) de GitHub" -ForegroundColor Yellow
Write-Host "Generalo en: https://github.com/settings/tokens" -ForegroundColor Yellow
Write-Host "Permisos necesarios: repo (Full control of private repositories)" -ForegroundColor Yellow
Write-Host ""
$token = Read-Host "Ingresa tu GitHub Personal Access Token" -AsSecureString
$tokenPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($token))

# Headers para autenticación
$headers = @{
    "Authorization" = "token $tokenPlain"
    "Accept" = "application/vnd.github.v3+json"
}

Write-Host ""
Write-Host "[1/4] Buscando release con tag '$Tag'..." -ForegroundColor Cyan

# Obtener ID del release
$releaseUrl = "https://api.github.com/repos/$Owner/$Repo/releases/tags/$Tag"

try {
    $release = Invoke-RestMethod -Uri $releaseUrl -Headers $headers -Method Get
    $releaseId = $release.id
    Write-Host "[OK] Release encontrado: ID = $releaseId" -ForegroundColor Green
    Write-Host "     Nombre: $($release.name)"
    Write-Host "     Creado: $($release.created_at)"
}
catch {
    Write-Host "[ERROR] No se pudo encontrar release con tag '$Tag'" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Verifica que:" -ForegroundColor Yellow
    Write-Host "  1. El release existe en GitHub"
    Write-Host "  2. El tag es correcto (sensible a mayusculas)"
    Write-Host "  3. El token tiene permisos 'repo'"
    Throw
}

Write-Host ""
Write-Host "[2/4] Verificando assets existentes..." -ForegroundColor Cyan

# Verificar si el asset ya existe
$existingAsset = $release.assets | Where-Object { $_.name -eq $fileName }

if ($existingAsset) {
    Write-Host "[WARN] El asset '$fileName' ya existe en este release" -ForegroundColor Yellow
    $overwrite = Read-Host "Quieres eliminarlo y resubir? (s/n)"
    
    if ($overwrite -eq 's' -or $overwrite -eq 'S') {
        Write-Host "[3/4] Eliminando asset existente..." -ForegroundColor Cyan
        $deleteUrl = "https://api.github.com/repos/$Owner/$Repo/releases/assets/$($existingAsset.id)"
        
        try {
            Invoke-RestMethod -Uri $deleteUrl -Headers $headers -Method Delete | Out-Null
            Write-Host "[OK] Asset eliminado" -ForegroundColor Green
        }
        catch {
            Write-Host "[ERROR] No se pudo eliminar asset existente" -ForegroundColor Red
            Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
            Throw
        }
    }
    else {
        Write-Host "[CANCEL] Operacion cancelada por usuario" -ForegroundColor Yellow
        Throw
    }
}
else {
    Write-Host "[OK] No hay conflictos de nombres" -ForegroundColor Green
}

Write-Host ""
Write-Host "[4/4] Subiendo asset '$fileName' ($fileSize MB)..." -ForegroundColor Cyan
Write-Host "      Esto puede tomar varios minutos..." -ForegroundColor Yellow

# URL para subir asset
$uploadUrl = "https://uploads.github.com/repos/$Owner/$Repo/releases/$releaseId/assets?name=$fileName"

# Headers para upload
$uploadHeaders = @{
    "Authorization" = "token $tokenPlain"
    "Content-Type" = "application/zip"
}

# Leer archivo como bytes
$fileBytes = [System.IO.File]::ReadAllBytes($file.FullName)

try {
    # Subir asset (con timeout extendido)
    $ProgressPreference = 'SilentlyContinue'  # Desactivar barra de progreso nativa
    
    $response = Invoke-RestMethod -Uri $uploadUrl `
                                   -Headers $uploadHeaders `
                                   -Method Post `
                                   -Body $fileBytes `
                                   -TimeoutSec 600  # 10 minutos de timeout
    
    Write-Host ""
    Write-Host "=" * 70
    Write-Host "[EXITO] Asset subido correctamente!" -ForegroundColor Green
    Write-Host "=" * 70
    Write-Host "Nombre:      $($response.name)"
    Write-Host "Tamano:      $([math]::Round($response.size/1MB, 2)) MB"
    Write-Host "URL:         $($response.browser_download_url)"
    Write-Host "Descargas:   $($response.download_count)"
    Write-Host ""
}
catch {
    Write-Host ""
    Write-Host "[ERROR] Fallo al subir asset" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $errorBody = $reader.ReadToEnd()
        Write-Host "Detalles: $errorBody" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "Posibles causas:" -ForegroundColor Yellow
    Write-Host "  1. Conexion de red inestable"
    Write-Host "  2. Token sin permisos suficientes"
    Write-Host "  3. Limite de tamano de GitHub excedido"
    Throw
}
