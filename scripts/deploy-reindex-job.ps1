param(
    [string]$ProjectId = "project-838503ae-99e5-4041-837",
    [string]$Region = "us-central1",
    [string]$Repository = "tesis-producto",
    [string]$ImageName = "backend",
    [string]$Tag = "latest",
    [string]$JobName = "tesis-producto-reindex",
    [string]$EnvFile = "",
    [string]$ServiceAccount = "",
    [string]$DocumentStorageBackend = "",
    [string]$Memory = "4Gi",
    [string]$Cpu = "4",
    [string]$TaskTimeout = "60m",
    [switch]$ExecuteNow
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $root
$image = "$Region-docker.pkg.dev/$ProjectId/$Repository/$ImageName`:$Tag"

if ([string]::IsNullOrWhiteSpace($EnvFile)) {
    $EnvFile = Join-Path $projectRoot "backend\cloudrun.env.yaml"
}

if (-not (Test-Path $EnvFile)) {
    throw "No se encontro el archivo de variables para Cloud Run Job: $EnvFile"
}

$envFileForDeploy = $EnvFile
$tempEnvFile = $null
try {
    if (-not [string]::IsNullOrWhiteSpace($DocumentStorageBackend)) {
        $envLines = Get-Content $EnvFile
        $updatedEnvLines = @()
        $overrideApplied = $false
        foreach ($line in $envLines) {
            if ($line -match "^\s*DOCUMENT_STORAGE_BACKEND\s*:") {
                $updatedEnvLines += "DOCUMENT_STORAGE_BACKEND: ""$DocumentStorageBackend"""
                $overrideApplied = $true
            } else {
                $updatedEnvLines += $line
            }
        }
        if (-not $overrideApplied) {
            $updatedEnvLines += "DOCUMENT_STORAGE_BACKEND: ""$DocumentStorageBackend"""
        }

        $tempEnvFile = [System.IO.Path]::GetTempFileName()
        Set-Content -LiteralPath $tempEnvFile -Value $updatedEnvLines
        $envFileForDeploy = $tempEnvFile
    }
}
catch {
    if ($tempEnvFile -and (Test-Path $tempEnvFile)) {
        Remove-Item -LiteralPath $tempEnvFile -Force
    }
    throw
}

$jobExists = $false
$jobsJson = & gcloud run jobs list `
    --project $ProjectId `
    --region $Region `
    --format "json"

if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($jobsJson)) {
    $jobs = $jobsJson | ConvertFrom-Json
    if ($jobs -is [System.Array]) {
        $jobExists = $null -ne ($jobs | Where-Object { $_.metadata.name -eq $JobName } | Select-Object -First 1)
    } elseif ($null -ne $jobs) {
        $jobExists = $jobs.metadata.name -eq $JobName
    }
}

$baseArgs = @(
    "run", "jobs"
)

if ($jobExists) {
    Write-Host "Actualizando Cloud Run Job existente..." -ForegroundColor Cyan
    $baseArgs += @(
        "update", $JobName,
        "--project", $ProjectId,
        "--region", $Region,
        "--image", $image,
        "--command", "python",
        "--args=-m,app.reindex_job",
        "--env-vars-file", $envFileForDeploy,
        "--memory", $Memory,
        "--cpu", $Cpu,
        "--task-timeout", $TaskTimeout
    )
} else {
    Write-Host "Creando Cloud Run Job..." -ForegroundColor Cyan
    $baseArgs += @(
        "create", $JobName,
        "--project", $ProjectId,
        "--region", $Region,
        "--image", $image,
        "--command", "python",
        "--args=-m,app.reindex_job",
        "--env-vars-file", $envFileForDeploy,
        "--memory", $Memory,
        "--cpu", $Cpu,
        "--task-timeout", $TaskTimeout
    )
}

if (-not [string]::IsNullOrWhiteSpace($ServiceAccount)) {
    $baseArgs += @("--service-account", $ServiceAccount)
}

if ($ExecuteNow) {
    $baseArgs += "--execute-now"
}

try {
    & gcloud @baseArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo el despliegue del Cloud Run Job '$JobName'. Revisa la salida de gcloud para mas detalle."
    }

    Write-Host ""
    Write-Host "Cloud Run Job listo: $JobName" -ForegroundColor Green
    Write-Host "Imagen: $image"
    Write-Host "Env file: $EnvFile"
    Write-Host "Memory: $Memory"
    Write-Host "CPU: $Cpu"
    Write-Host "Task timeout: $TaskTimeout"
    if (-not [string]::IsNullOrWhiteSpace($DocumentStorageBackend)) {
        Write-Host "DOCUMENT_STORAGE_BACKEND: $DocumentStorageBackend"
    }
}
finally {
    if ($tempEnvFile -and (Test-Path $tempEnvFile)) {
        Remove-Item -LiteralPath $tempEnvFile -Force
    }
}
