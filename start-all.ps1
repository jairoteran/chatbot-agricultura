param(
    [switch]$NoNewWindows
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"
$venvPython = Join-Path $backendDir ".venv\Scripts\python.exe"
$activateScript = Join-Path $backendDir ".venv\Scripts\Activate.ps1"

if (-not (Test-Path $backendDir)) {
    throw "No se encontro la carpeta 'backend' en $root."
}

if (-not (Test-Path $frontendDir)) {
    throw "No se encontro la carpeta 'frontend' en $root."
}

if (-not (Test-Path $venvPython)) {
    throw "No se encontro el entorno virtual del backend. Crea 'backend\.venv' e instala dependencias antes de ejecutar este script."
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm no esta disponible en esta terminal. Instala Node.js antes de ejecutar este script."
}

$backendCommand = "& '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --reload --port 8000"
$frontendCommand = "npm run dev"

Write-Host "Iniciando backend en http://localhost:8000 ..."
if ($NoNewWindows) {
    Start-Job -Name "pdf-chat-backend" -ScriptBlock {
        param($workingDir, $command)
        Set-Location -LiteralPath $workingDir
        Invoke-Expression $command
    } -ArgumentList $backendDir, $backendCommand | Out-Null
} else {
    Start-Process powershell -WorkingDirectory $backendDir -ArgumentList @(
        "-NoExit",
        "-Command",
        $backendCommand
    ) | Out-Null
}

Write-Host "Iniciando frontend en http://localhost:5173 ..."
if ($NoNewWindows) {
    Start-Job -Name "pdf-chat-frontend" -ScriptBlock {
        param($workingDir, $command)
        Set-Location -LiteralPath $workingDir
        Invoke-Expression $command
    } -ArgumentList $frontendDir, $frontendCommand | Out-Null

    Write-Host ""
    Write-Host "Servicios iniciados en segundo plano con Start-Job."
    Write-Host "Para verlos: Get-Job"
    Write-Host "Para detenerlos: Get-Job | Stop-Job"
    Write-Host "Para limpiar jobs: Get-Job | Remove-Job"
} else {
    Start-Process powershell -WorkingDirectory $frontendDir -ArgumentList @(
        "-NoExit",
        "-Command",
        $frontendCommand
    ) | Out-Null

    Write-Host ""
    Write-Host "Listo. Se abrieron dos ventanas de PowerShell:"
    Write-Host "- Backend: http://localhost:8000"
    Write-Host "- Frontend: http://localhost:5173"
}
