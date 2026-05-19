param(
    [string]$ProjectId = "project-838503ae-99e5-4041-837",
    [string]$Bucket = "tesis-producto-dev-documents",
    [string]$Prefix = "documents",
    [string]$SourceDir = "",
    [switch]$DeleteUnmatchedDestinationObjects
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $root

if ([string]::IsNullOrWhiteSpace($SourceDir)) {
    $SourceDir = Join-Path $projectRoot "backend\data"
}

if (-not (Test-Path $SourceDir)) {
    throw "No se encontro el directorio de origen: $SourceDir"
}

$destination = "gs://$Bucket"
if (-not [string]::IsNullOrWhiteSpace($Prefix)) {
    $destination = "$destination/$($Prefix.Trim('/'))"
}

Write-Host "Sincronizando documentos al bucket..." -ForegroundColor Cyan
Write-Host "Origen: $SourceDir"
Write-Host "Destino: $destination"

$tempStageDir = Join-Path ([System.IO.Path]::GetTempPath()) ("tesis-doc-sync-" + [System.Guid]::NewGuid().ToString("N"))

try {
    New-Item -ItemType Directory -Path $tempStageDir | Out-Null

    $pdfFiles = Get-ChildItem -Path $SourceDir -Recurse -File -Filter *.pdf
    if (-not $pdfFiles) {
        throw "No se encontraron archivos PDF en $SourceDir"
    }

    foreach ($file in $pdfFiles) {
        $relativePath = $file.FullName.Substring($SourceDir.Length).TrimStart('\', '/')
        $destinationPath = Join-Path $tempStageDir $relativePath
        $destinationDir = Split-Path -Parent $destinationPath
        if (-not (Test-Path $destinationDir)) {
            New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
        }
        Copy-Item -LiteralPath $file.FullName -Destination $destinationPath -Force
    }

    $rsyncArgs = @("storage", "rsync", $tempStageDir, $destination, "--recursive", "--project", $ProjectId)
    if ($DeleteUnmatchedDestinationObjects) {
        $rsyncArgs += "--delete-unmatched-destination-objects"
    }

    & gcloud @rsyncArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo la sincronizacion de documentos hacia $destination."
    }
}
finally {
    if (Test-Path $tempStageDir) {
        Remove-Item -LiteralPath $tempStageDir -Recurse -Force
    }
}

Write-Host ""
Write-Host "Documentos sincronizados correctamente." -ForegroundColor Green
Write-Host "Origen: $SourceDir"
Write-Host "Destino: $destination"
if ($DeleteUnmatchedDestinationObjects) {
    Write-Host "Limpieza destino: activada"
}
