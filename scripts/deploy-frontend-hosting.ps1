[CmdletBinding()]
param(
    [string]$ProjectId = "project-838503ae-99e5-4041-837",
    [string]$FrontendDir = (Join-Path $PSScriptRoot "..\\frontend"),
    [string]$HostingSiteId = "tesis-producto-1025954944056",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$frontendPath = [System.IO.Path]::GetFullPath($FrontendDir)
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$firebaseConfig = Join-Path $repoRoot "firebase.json"
$firebaseRc = Join-Path $repoRoot ".firebaserc"

if (-not (Test-Path $frontendPath)) {
    throw "No se encontro el directorio del frontend: $frontendPath"
}

if (-not (Test-Path $firebaseConfig)) {
    throw "No se encontro firebase.json en la raiz del repositorio: $firebaseConfig"
}

if (-not (Test-Path $firebaseRc)) {
    throw "No se encontro .firebaserc en la raiz del repositorio: $firebaseRc"
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "No se encontro npm en PATH. Instala Node.js o abre una terminal con npm disponible."
}

$firebaseCommand = Get-Command firebase -ErrorAction SilentlyContinue
$useNpxFirebase = $false

if (-not $firebaseCommand) {
    if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
        throw "No se encontro Firebase CLI en PATH ni tampoco npx. Instala Node.js y usa 'npx firebase-tools login' o instala 'firebase-tools'."
    }
    $useNpxFirebase = $true
}

Push-Location $repoRoot

try {
    if (-not $SkipBuild) {
        Write-Host "Compilando frontend para produccion..." -ForegroundColor Cyan
        & npm --prefix $frontendPath run build
        if ($LASTEXITCODE -ne 0) {
            throw "Fallo la compilacion del frontend."
        }
    }

    Write-Host "Desplegando frontend en Firebase Hosting..." -ForegroundColor Cyan
    if ($useNpxFirebase) {
        & npx firebase-tools deploy --only hosting --project $ProjectId
    }
    else {
        & firebase deploy --only hosting --project $ProjectId
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo el despliegue del frontend en Firebase Hosting."
    }

    Write-Host "Frontend desplegado correctamente en Firebase Hosting." -ForegroundColor Green
    Write-Host "Proyecto Firebase: $ProjectId" -ForegroundColor Green
    Write-Host "Hosting site: $HostingSiteId" -ForegroundColor Green
    Write-Host "Rewrite API: /api/** -> Cloud Run service tesis-producto-api (us-central1)" -ForegroundColor Green
}
finally {
    Pop-Location
}
