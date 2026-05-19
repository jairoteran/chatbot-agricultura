param(
    [string]$ProjectId = "project-838503ae-99e5-4041-837",
    [string]$Region = "us-central1",
    [string]$Repository = "tesis-producto",
    [string]$ImageName = "backend",
    [string]$Tag = "latest"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $root
$image = "$Region-docker.pkg.dev/$ProjectId/$Repository/$ImageName`:$Tag"
$cloudbuildConfig = Join-Path $projectRoot "backend\cloudbuild.backend.yaml"

Write-Host "Construyendo imagen del backend..." -ForegroundColor Cyan
Write-Host "Imagen destino: $image"

& gcloud builds submit $projectRoot `
  --project $ProjectId `
  --region $Region `
  --config $cloudbuildConfig `
  --substitutions "_IMAGE=$image"

if ($LASTEXITCODE -ne 0) {
    throw "Fallo el build de la imagen del backend."
}

Write-Host ""
Write-Host "Build completado." -ForegroundColor Green
Write-Host "Imagen: $image"
