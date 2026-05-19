param(
    [string]$ProjectId = "project-838503ae-99e5-4041-837",
    [string]$Region = "us-central1",
    [string]$Repository = "tesis-producto",
    [string]$ImageName = "backend",
    [string]$Tag = "latest",
    [string]$ServiceName = "tesis-producto-api",
    [string]$EnvFile = "",
    [string]$ServiceAccount = "",
    [string]$GeminiApiSecret = "",
    [string]$AdminSessionSecret = "",
    [string]$Memory = "1Gi",
    [string]$AllowRuntimeReindex = "false",
    [string]$DocumentStorageBackend = "",
    [string]$CorsOrigins = "",
    [string]$GoogleAuthClientId = "",
    [string]$AdminEmails = "",
    [string]$AdminBasePath = "",
    [switch]$AllowUnauthenticated = $true
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $root
$image = "$Region-docker.pkg.dev/$ProjectId/$Repository/$ImageName`:$Tag"

if ([string]::IsNullOrWhiteSpace($EnvFile)) {
    $EnvFile = Join-Path $projectRoot "backend\cloudrun.env.yaml"
}

if (-not (Test-Path $EnvFile)) {
    throw "No se encontro el archivo de variables para Cloud Run service: $EnvFile"
}

$envFileForDeploy = $EnvFile
$tempEnvFile = $null
try {
    $envLines = Get-Content $EnvFile
    $updatedEnvLines = @()
    $overrideApplied = $false
    $documentOverrideApplied = $false
    $corsOverrideApplied = $false
    $googleAuthClientIdApplied = $false
    $adminEmailsApplied = $false
    $adminBasePathApplied = $false
    foreach ($line in $envLines) {
        if ($line -match "^\s*ALLOW_RUNTIME_REINDEX\s*:") {
            $updatedEnvLines += "ALLOW_RUNTIME_REINDEX: ""$AllowRuntimeReindex"""
            $overrideApplied = $true
        } elseif (-not [string]::IsNullOrWhiteSpace($DocumentStorageBackend) -and $line -match "^\s*DOCUMENT_STORAGE_BACKEND\s*:") {
            $updatedEnvLines += "DOCUMENT_STORAGE_BACKEND: ""$DocumentStorageBackend"""
            $documentOverrideApplied = $true
        } elseif (-not [string]::IsNullOrWhiteSpace($CorsOrigins) -and $line -match "^\s*CORS_ORIGINS\s*:") {
            $updatedEnvLines += "CORS_ORIGINS: ""$CorsOrigins"""
            $corsOverrideApplied = $true
        } elseif (-not [string]::IsNullOrWhiteSpace($GoogleAuthClientId) -and $line -match "^\s*GOOGLE_AUTH_CLIENT_ID\s*:") {
            $updatedEnvLines += "GOOGLE_AUTH_CLIENT_ID: ""$GoogleAuthClientId"""
            $googleAuthClientIdApplied = $true
        } elseif (-not [string]::IsNullOrWhiteSpace($AdminEmails) -and $line -match "^\s*ADMIN_EMAILS\s*:") {
            $updatedEnvLines += "ADMIN_EMAILS: ""$AdminEmails"""
            $adminEmailsApplied = $true
        } elseif (-not [string]::IsNullOrWhiteSpace($AdminBasePath) -and $line -match "^\s*ADMIN_BASE_PATH\s*:") {
            $updatedEnvLines += "ADMIN_BASE_PATH: ""$AdminBasePath"""
            $adminBasePathApplied = $true
        } else {
            $updatedEnvLines += $line
        }
    }
    if (-not $overrideApplied) {
        $updatedEnvLines += "ALLOW_RUNTIME_REINDEX: ""$AllowRuntimeReindex"""
    }
    if (-not [string]::IsNullOrWhiteSpace($DocumentStorageBackend) -and -not $documentOverrideApplied) {
        $updatedEnvLines += "DOCUMENT_STORAGE_BACKEND: ""$DocumentStorageBackend"""
    }
    if (-not [string]::IsNullOrWhiteSpace($CorsOrigins) -and -not $corsOverrideApplied) {
        $updatedEnvLines += "CORS_ORIGINS: ""$CorsOrigins"""
    }
    if (-not [string]::IsNullOrWhiteSpace($GoogleAuthClientId) -and -not $googleAuthClientIdApplied) {
        $updatedEnvLines += "GOOGLE_AUTH_CLIENT_ID: ""$GoogleAuthClientId"""
    }
    if (-not [string]::IsNullOrWhiteSpace($AdminEmails) -and -not $adminEmailsApplied) {
        $updatedEnvLines += "ADMIN_EMAILS: ""$AdminEmails"""
    }
    if (-not [string]::IsNullOrWhiteSpace($AdminBasePath) -and -not $adminBasePathApplied) {
        $updatedEnvLines += "ADMIN_BASE_PATH: ""$AdminBasePath"""
    }

    $tempEnvFile = [System.IO.Path]::GetTempFileName()
    Set-Content -LiteralPath $tempEnvFile -Value $updatedEnvLines
    $envFileForDeploy = $tempEnvFile
}
catch {
    if ($tempEnvFile -and (Test-Path $tempEnvFile)) {
        Remove-Item -LiteralPath $tempEnvFile -Force
    }
    throw
}

$serviceExists = $false
$servicesJson = & gcloud run services list `
    --project $ProjectId `
    --region $Region `
    --format "json"

if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($servicesJson)) {
    $services = $servicesJson | ConvertFrom-Json
    if ($services -is [System.Array]) {
        $serviceExists = $null -ne ($services | Where-Object { $_.metadata.name -eq $ServiceName } | Select-Object -First 1)
    } elseif ($null -ne $services) {
        $serviceExists = $services.metadata.name -eq $ServiceName
    }
}

$baseArgs = @(
    "run", "deploy", $ServiceName,
    "--project", $ProjectId,
    "--region", $Region,
    "--image", $image,
    "--platform", "managed",
    "--env-vars-file", $envFileForDeploy,
    "--memory", $Memory
)

if ($AllowUnauthenticated) {
    $baseArgs += "--allow-unauthenticated"
} else {
    $baseArgs += "--no-allow-unauthenticated"
}

if (-not [string]::IsNullOrWhiteSpace($ServiceAccount)) {
    $baseArgs += @("--service-account", $ServiceAccount)
}

if (-not [string]::IsNullOrWhiteSpace($GeminiApiSecret)) {
    $baseArgs += @("--set-secrets", "GEMINI_API_KEY=$GeminiApiSecret`:latest")
}
if (-not [string]::IsNullOrWhiteSpace($AdminSessionSecret)) {
    $baseArgs += @("--set-secrets", "ADMIN_SESSION_SECRET=$AdminSessionSecret`:latest")
}

try {
    if ($serviceExists) {
        Write-Host "Actualizando Cloud Run service existente..." -ForegroundColor Cyan
    } else {
        Write-Host "Creando Cloud Run service..." -ForegroundColor Cyan
    }

    & gcloud @baseArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo el despliegue del Cloud Run service '$ServiceName'. Revisa la salida de gcloud para mas detalle."
    }

    Write-Host ""
    Write-Host "Cloud Run service listo: $ServiceName" -ForegroundColor Green
    Write-Host "Imagen: $image"
    Write-Host "Env file: $EnvFile"
    Write-Host "Memory: $Memory"
    Write-Host "ALLOW_RUNTIME_REINDEX: $AllowRuntimeReindex"
    if (-not [string]::IsNullOrWhiteSpace($DocumentStorageBackend)) {
        Write-Host "DOCUMENT_STORAGE_BACKEND: $DocumentStorageBackend"
    }
    if (-not [string]::IsNullOrWhiteSpace($CorsOrigins)) {
        Write-Host "CORS_ORIGINS: $CorsOrigins"
    }
    if (-not [string]::IsNullOrWhiteSpace($GoogleAuthClientId)) {
        Write-Host "GOOGLE_AUTH_CLIENT_ID: $GoogleAuthClientId"
    }
    if (-not [string]::IsNullOrWhiteSpace($AdminEmails)) {
        Write-Host "ADMIN_EMAILS: $AdminEmails"
    }
    if (-not [string]::IsNullOrWhiteSpace($AdminBasePath)) {
        Write-Host "ADMIN_BASE_PATH: $AdminBasePath"
    }
    if (-not [string]::IsNullOrWhiteSpace($GeminiApiSecret)) {
        Write-Host "Secret Gemini: $GeminiApiSecret"
    }
    if (-not [string]::IsNullOrWhiteSpace($AdminSessionSecret)) {
        Write-Host "Secret Admin Session: $AdminSessionSecret"
    }
}
finally {
    if ($tempEnvFile -and (Test-Path $tempEnvFile)) {
        Remove-Item -LiteralPath $tempEnvFile -Force
    }
}
