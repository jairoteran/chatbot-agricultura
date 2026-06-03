$ErrorActionPreference = "Stop"

$root = "C:\Users\Jairo Teran\Downloads\Tesis\Producto"
$healthUrl = "http://127.0.0.1:8000/health"
$reindexUrl = "http://127.0.0.1:8000/reindex"

Write-Host "Esperando a que el backend local este disponible para reindexar..." -ForegroundColor Yellow

$health = $null
do {
    try {
        $health = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 10
        Write-Host ("Estado actual: " + $health.status + " | " + $health.detail)
    }
    catch {
        $health = $null
        Write-Host "Backend aun no responde. Reintentando..." -ForegroundColor DarkYellow
        Start-Sleep -Seconds 3
    }
} while ($null -eq $health)

while ($health.status -eq "checking") {
    Start-Sleep -Seconds 3
    try {
        $health = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 10
        Write-Host ("Estado actual: " + $health.status + " | " + $health.detail)
    }
    catch {
        $health = $null
        Write-Host "Se perdio la conexion con el backend. Reintentando..." -ForegroundColor DarkYellow
        do {
            Start-Sleep -Seconds 3
            try {
                $health = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 10
                Write-Host ("Estado actual: " + $health.status + " | " + $health.detail)
            }
            catch {
                $health = $null
                Write-Host "Backend aun no responde. Reintentando..." -ForegroundColor DarkYellow
            }
        } while ($null -eq $health)
    }
}

if ($health.status -eq "error") {
    Write-Host ""
    Write-Host "El backend reporto un error durante la inicializacion:" -ForegroundColor Red
    Write-Host $health.detail
    Write-Host ""
    Read-Host "Presiona Enter para cerrar esta ventana"
    exit 1
}

Write-Host ""
Write-Host "Lanzando reindexado local..." -ForegroundColor Cyan

$job = $null

try {
    $job = Start-Job -ScriptBlock {
        param($Uri)
        Invoke-RestMethod -Uri $Uri -Method Post -TimeoutSec 3600
    } -ArgumentList $reindexUrl

    $lastProgressLine = ""
    while ($job.State -eq "Running") {
        Start-Sleep -Seconds 2

        try {
            $health = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 10
            $progress = 0
            if ($null -ne $health.init_progress) {
                $progress = [int]$health.init_progress
            }

            $stage = if ([string]::IsNullOrWhiteSpace($health.init_stage)) { "reindexing" } else { $health.init_stage }
            $detail = if ([string]::IsNullOrWhiteSpace($health.detail)) { "Procesando..." } else { $health.detail }
            $progressLine = ("[{0,3}%] {1} | {2}" -f $progress, $stage, $detail)

            Write-Progress -Id 1 -Activity "Reindexando documentos" -Status $detail -PercentComplete $progress
            if ($progressLine -ne $lastProgressLine) {
                Write-Host $progressLine -ForegroundColor DarkCyan
                $lastProgressLine = $progressLine
            }
        }
        catch {
            Write-Host "No se pudo consultar el progreso en /health. Reintentando..." -ForegroundColor DarkYellow
        }
    }
    Write-Progress -Id 1 -Activity "Reindexando documentos" -Completed
    $result = Receive-Job -Job $job -ErrorAction Stop
    $result | ConvertTo-Json -Depth 6
    Write-Host ""
    Write-Host "Reindexado completado." -ForegroundColor Green
}
catch {
    Write-Progress -Id 1 -Activity "Reindexando documentos" -Completed
    Write-Host ""
    Write-Host "Fallo el reindexado:" -ForegroundColor Red
    Write-Host $_
}
finally {
    if ($null -ne $job) {
        Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ""
Read-Host "Presiona Enter para cerrar esta ventana"
