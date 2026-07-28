<#
.SYNOPSIS
    Exporta una copia limpia del codigo fuente del proyecto para SENADI.
.DESCRIPTION
    Copia codigo fuente, documentacion y scripts utiles, excluyendo dependencias,
    builds, secretos, PDFs locales, indices y caches generados.
#>

param(
    [string]$OutputDir = (Join-Path ([Environment]::GetFolderPath("UserProfile")) "Downloads\codigo_limpio")
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
$ExportSourceDir = Join-Path $OutputDir "codigo_fuente"
$ZipPath = Join-Path $OutputDir "senadi_agroj_especializado.zip"

Write-Host "==> Preparando directorio de salida: $OutputDir" -ForegroundColor Cyan
if (Test-Path $OutputDir) {
    if (Test-Path $ExportSourceDir) {
        Remove-Item -Recurse -Force $ExportSourceDir
    }
    if (Test-Path $ZipPath) {
        Remove-Item -Force $ZipPath
    }
} else {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

New-Item -ItemType Directory -Path $ExportSourceDir -Force | Out-Null

function Copy-IfExists {
    param(
        [string]$Source,
        [string]$Destination
    )

    if (Test-Path $Source) {
        $destinationParent = Split-Path -Parent $Destination
        if (-not (Test-Path $destinationParent)) {
            New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null
        }
        Copy-Item -LiteralPath $Source -Destination $Destination -Force
    }
}

function Copy-CleanDirectory {
    param(
        [string]$SourcePath,
        [string]$DestinationPath,
        [string[]]$ExcludePatterns
    )

    if (-not (Test-Path $SourcePath)) {
        return
    }

    New-Item -ItemType Directory -Path $DestinationPath -Force | Out-Null

    Get-ChildItem -LiteralPath $SourcePath -Force | ForEach-Object {
        $item = $_
        foreach ($pattern in $ExcludePatterns) {
            if ($item.Name -like $pattern) {
                Write-Host "    [Excluido] $($item.FullName)" -ForegroundColor Yellow
                return
            }
        }

        $destination = Join-Path $DestinationPath $item.Name
        if ($item.PSIsContainer) {
            Copy-CleanDirectory -SourcePath $item.FullName -DestinationPath $destination -ExcludePatterns $ExcludePatterns
        } else {
            Copy-Item -LiteralPath $item.FullName -Destination $destination -Force
        }
    }
}

Write-Host "==> Copiando archivos raiz..." -ForegroundColor Cyan
$rootFiles = @(
    "README.md",
    ".gitignore",
    ".gcloudignore",
    ".python-version",
    "firebase.json",
    ".firebaserc",
    "gcs-cors.json",
    "requirements.txt",
    "start-all.ps1"
)

foreach ($file in $rootFiles) {
    Copy-IfExists -Source (Join-Path $ProjectRoot $file) -Destination (Join-Path $ExportSourceDir $file)
}

Write-Host "==> Copiando backend..." -ForegroundColor Cyan
Copy-CleanDirectory `
    -SourcePath (Join-Path $ProjectRoot "backend") `
    -DestinationPath (Join-Path $ExportSourceDir "backend") `
    -ExcludePatterns @(".venv", ".env", "__pycache__", "*.pyc", "data", "storage")

Write-Host "==> Copiando frontend..." -ForegroundColor Cyan
Copy-CleanDirectory `
    -SourcePath (Join-Path $ProjectRoot "frontend") `
    -DestinationPath (Join-Path $ExportSourceDir "frontend") `
    -ExcludePatterns @("node_modules", "dist", ".env", "__pycache__")

Write-Host "==> Copiando docs..." -ForegroundColor Cyan
Copy-CleanDirectory `
    -SourcePath (Join-Path $ProjectRoot "docs") `
    -DestinationPath (Join-Path $ExportSourceDir "docs") `
    -ExcludePatterns @("__pycache__")

Write-Host "==> Copiando scripts..." -ForegroundColor Cyan
Copy-CleanDirectory `
    -SourcePath (Join-Path $ProjectRoot "scripts") `
    -DestinationPath (Join-Path $ExportSourceDir "scripts") `
    -ExcludePatterns @("__pycache__")

Write-Host "==> Creando ZIP: $ZipPath" -ForegroundColor Cyan
Compress-Archive -Path "$ExportSourceDir\*" -DestinationPath $ZipPath -Force

$zipItem = Get-Item $ZipPath
$zipSizeMb = [math]::Round($zipItem.Length / 1MB, 2)

Write-Host "==========================================================" -ForegroundColor Green
Write-Host " Paquete SENADI generado correctamente" -ForegroundColor Green
Write-Host " Carpeta limpia: $ExportSourceDir" -ForegroundColor Green
Write-Host " ZIP: $ZipPath ($zipSizeMb MB)" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
