param(
    [string]$ProjectId = "project-838503ae-99e5-4041-837",
    [string]$SecretName = "GEMINI_API_KEY",
    [string]$SecretValue = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($SecretValue)) {
    throw "Debes enviar el valor del secreto con -SecretValue."
}

$secretExists = $false
$secretsJson = & gcloud secrets list `
    --project $ProjectId `
    --format "json"

if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($secretsJson)) {
    $secrets = $secretsJson | ConvertFrom-Json
    if ($secrets -is [System.Array]) {
        $secretExists = $null -ne ($secrets | Where-Object { $_.name -match "/secrets/$SecretName$" } | Select-Object -First 1)
    } elseif ($null -ne $secrets) {
        $secretExists = $secrets.name -match "/secrets/$SecretName$"
    }
}

if (-not $secretExists) {
    Write-Host "Creando secreto en Secret Manager..." -ForegroundColor Cyan
    & gcloud secrets create $SecretName `
        --project $ProjectId `
        --replication-policy "automatic"

    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo crear el secreto '$SecretName'."
    }
}

$tempFile = [System.IO.Path]::GetTempFileName()
try {
    Set-Content -LiteralPath $tempFile -Value $SecretValue -NoNewline

    Write-Host "Agregando nueva version del secreto..." -ForegroundColor Cyan
    & gcloud secrets versions add $SecretName `
        --project $ProjectId `
        --data-file $tempFile

    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo agregar una nueva version al secreto '$SecretName'."
    }
}
finally {
    if (Test-Path $tempFile) {
        Remove-Item -LiteralPath $tempFile -Force
    }
}

Write-Host ""
Write-Host "Secreto listo: $SecretName" -ForegroundColor Green
