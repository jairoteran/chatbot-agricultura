[CmdletBinding()]
param(
    [string]$ProjectId = "project-838503ae-99e5-4041-837",
    [string]$Region = "us-central1",
    [string]$Repository = "tesis-producto",
    [string]$ImageName = "frontend",
    [string]$Tag = "latest",
    [string]$ApiBaseUrl = "/api",
    [string]$AdminBasePath = "/gestion",
    [string]$BasePath = "/"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $root
$image = "$Region-docker.pkg.dev/$ProjectId/$Repository/$ImageName`:$Tag"

$substitutions = @(
    "_IMAGE=$image",
    "_VITE_API_URL=$ApiBaseUrl/chat",
    "_VITE_HEALTH_URL=$ApiBaseUrl/health",
    "_VITE_REINDEX_URL=$ApiBaseUrl/reindex",
    "_VITE_SUMMARY_URL=$ApiBaseUrl/summarize-document",
    "_VITE_ADMIN_CONFIG_URL=$ApiBaseUrl/admin/config",
    "_VITE_ADMIN_SESSION_URL=$ApiBaseUrl/admin/session",
    "_VITE_ADMIN_DOCUMENTS_URL=$ApiBaseUrl/admin/documents",
    "_VITE_ADMIN_BASE_PATH=$AdminBasePath",
    "_VITE_BASE_PATH=$BasePath"
) -join ","

Write-Host "Construyendo imagen del frontend..." -ForegroundColor Cyan

Push-Location $projectRoot
try {
    & gcloud builds submit . `
        --config frontend/cloudbuild.frontend.yaml `
        --substitutions $substitutions

    if ($LASTEXITCODE -ne 0) {
        throw "Fallo el build de la imagen del frontend."
    }

    Write-Host ""
    Write-Host "Build completado." -ForegroundColor Green
    Write-Host "Imagen: $image"
    Write-Host "API base embebida: $ApiBaseUrl"
    Write-Host "Ruta admin embebida: $AdminBasePath"
}
finally {
    Pop-Location
}
