[CmdletBinding()]
param(
    [string]$ProjectId = "project-838503ae-99e5-4041-837",
    [string]$Region = "us-central1",
    [string]$Repository = "tesis-producto",
    [string]$ImageName = "frontend",
    [string]$Tag = "latest",
    [string]$ServiceName = "tesis-producto-frontend",
    [string]$Memory = "512Mi",
    [switch]$AllowUnauthenticated = $true
)

$ErrorActionPreference = "Stop"

$image = "$Region-docker.pkg.dev/$ProjectId/$Repository/$ImageName`:$Tag"

$args = @(
    "run", "deploy", $ServiceName,
    "--project", $ProjectId,
    "--region", $Region,
    "--image", $image,
    "--platform", "managed",
    "--memory", $Memory,
    "--port", "8080"
)

if ($AllowUnauthenticated) {
    $args += "--allow-unauthenticated"
}
else {
    $args += "--no-allow-unauthenticated"
}

Write-Host "Desplegando frontend en Cloud Run..." -ForegroundColor Cyan
& gcloud @args

if ($LASTEXITCODE -ne 0) {
    throw "Fallo el despliegue del frontend en Cloud Run."
}

Write-Host ""
Write-Host "Cloud Run service listo: $ServiceName" -ForegroundColor Green
Write-Host "Imagen: $image"
