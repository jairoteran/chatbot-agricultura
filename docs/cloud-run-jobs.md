# Operacion en Cloud Run y Cloud Run Jobs

Esta guia explica como construir, desplegar y monitorear AGROJ ESPECIALIZADO en Google Cloud.

## Servicios desplegados

| Servicio | Nombre actual | Funcion |
| --- | --- | --- |
| Backend API | `tesis-producto-api` | API FastAPI, chat, salud y gestion documental. |
| Frontend | `tesis-producto-frontend` | Sitio React compilado y servido con Nginx. |
| Reindexado | `tesis-producto-reindex` | Cloud Run Job para reconstruir el indice documental. |

Region:

```text
us-central1
```

Proyecto:

```text
project-838503ae-99e5-4041-837
```

## Imagen del backend

Archivo:

```text
backend/Dockerfile
```

La imagen:

- usa Python 3.12 slim
- instala dependencias del backend
- copia `backend/app`
- crea `storage/` vacio para runtime
- no copia PDFs
- no copia indices generados
- arranca la API con Uvicorn

Comando por defecto:

```text
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
```

## Imagen del frontend

Archivo:

```text
frontend/Dockerfile
```

La imagen:

- compila React + Vite
- sirve archivos estaticos con Nginx
- mantiene rutas `/api/**` hacia el backend

## Build del backend

Desde la raiz:

```powershell
.\scripts\build-backend-image.ps1
```

El build usa:

```text
backend/cloudbuild.backend.yaml
```

`.gcloudignore` evita subir al contexto:

- PDFs
- indices generados
- caches
- `.venv`
- `node_modules`
- docs
- logs

## Deploy del backend API

```powershell
.\scripts\deploy-backend-api.ps1 `
  -GeminiApiSecret GEMINI_API_KEY `
  -AdminSessionSecret ADMIN_SESSION_SECRET `
  -DocumentStorageBackend gcs `
  -AllowRuntimeReindex "false" `
  -Memory "4Gi" `
  -Cpu "4" `
  -Timeout "120s"
```

Regla importante:

- `ALLOW_RUNTIME_REINDEX=false` en la API.
- La API consulta indices publicados.
- La API no debe reconstruir indices pesados durante trafico web.

## Deploy del job de reindexado

Para un volumen normal:

```powershell
.\scripts\deploy-reindex-job.ps1 `
  -DocumentStorageBackend gcs `
  -Memory "4Gi" `
  -Cpu "4" `
  -TaskTimeout "60m"
```

Para un volumen grande, por ejemplo cientos de PDFs:

```powershell
.\scripts\deploy-reindex-job.ps1 `
  -DocumentStorageBackend gcs `
  -Memory "8Gi" `
  -Cpu "4" `
  -TaskTimeout "43200s"
```

`43200s` equivale a 12 horas.

## Ejecutar reindexado

```powershell
gcloud run jobs execute tesis-producto-reindex `
  --region us-central1
```

Ver ejecuciones:

```powershell
gcloud run jobs executions list `
  --job tesis-producto-reindex `
  --region us-central1
```

Describir una ejecucion:

```powershell
gcloud run jobs executions describe tesis-producto-reindex-XXXXX `
  --region us-central1
```

## Logs del reindexado

```powershell
gcloud logging read `
  'resource.type="cloud_run_job" AND resource.labels.job_name="tesis-producto-reindex"' `
  --limit 50 `
  --format "value(timestamp,textPayload)"
```

Para una ejecucion concreta:

```powershell
gcloud logging read `
  'resource.type="cloud_run_job" AND resource.labels.job_name="tesis-producto-reindex" AND labels."run.googleapis.com/execution_name"="tesis-producto-reindex-XXXXX"' `
  --limit 50 `
  --format "value(timestamp,textPayload)"
```

## Build y deploy del frontend

```powershell
.\scripts\build-frontend-image.ps1 `
  -ApiBaseUrl "/api" `
  -AdminBasePath "/gestion"

.\scripts\deploy-frontend-cloudrun.ps1
```

URL esperada:

```text
https://tesis-producto-frontend-1025954944056.us-central1.run.app
```

## Subida masiva de documentos

Subir una carpeta de PDFs:

```powershell
gcloud storage cp "C:\ruta\a\documentos\*.pdf" `
  gs://tesis-producto-dev-documents/documents/
```

Con subcarpetas:

```powershell
gcloud storage cp "C:\ruta\a\documentos\**" `
  gs://tesis-producto-dev-documents/documents/ `
  --recursive
```

Despues de subir, ejecutar reindexado.

## Monitoreo por health

```powershell
Invoke-RestMethod -Method Get `
  -Uri "https://tesis-producto-api-1025954944056.us-central1.run.app/health" |
  ConvertTo-Json -Depth 10
```

Campos utiles:

```text
status
index_ready
indexed_file_count
document_storage_backend
index_storage_backend
metadata_backend
runtime_last_reindex_status
runtime_reindex_progress
runtime_reindex_stage
runtime_reindex_total_documents
runtime_reindex_processed_documents
last_generation_status
```

Monitor simple:

```powershell
while ($true) {
  Clear-Host
  $h = Invoke-RestMethod -Method Get -Uri "https://tesis-producto-api-1025954944056.us-central1.run.app/health"
  [pscustomobject]@{
    Status = $h.runtime_last_reindex_status
    Progress = "$($h.runtime_reindex_progress)%"
    Stage = $h.runtime_reindex_stage
    Processed = "$($h.runtime_reindex_processed_documents)/$($h.runtime_reindex_total_documents)"
    Indexed = $h.indexed_file_count
  }
  Start-Sleep -Seconds 30
}
```

## Secretos

Secretos esperados:

```text
GEMINI_API_KEY
ADMIN_SESSION_SECRET
```

Crear o actualizar secreto:

```powershell
.\scripts\set-gemini-secret.ps1 -SecretId GEMINI_API_KEY -SecretValue "TU_CLAVE"
```

Para `ADMIN_SESSION_SECRET`, usar un valor largo y aleatorio.

## Problemas comunes

### Build falla por `backend/storage`

El Dockerfile ya no debe copiar `backend/storage`. Esa carpeta contiene artefactos generados y esta ignorada.

La imagen correcta crea la carpeta:

```dockerfile
RUN mkdir -p ./storage
```

### Job falla por memoria

Subir memoria:

```powershell
.\scripts\deploy-reindex-job.ps1 -DocumentStorageBackend gcs -Memory "8Gi" -Cpu "4" -TaskTimeout "43200s"
```

### Job falla por timeout

Subir `TaskTimeout`. Cloud Run Jobs soporta timeouts largos; para paquetes grandes usar 6 a 12 horas.

### API tarda en preparar sistema

Revisar:

```powershell
Invoke-RestMethod -Method Get -Uri "https://tesis-producto-api-1025954944056.us-central1.run.app/health" |
  ConvertTo-Json -Depth 10
```

Si el indice activo existe en GCS, la API debe poder arrancar usando el indice publicado sin reindexar.

## Orden recomendado de despliegue

1. Construir backend.
2. Desplegar backend API.
3. Desplegar o actualizar job de reindexado.
4. Construir frontend.
5. Desplegar frontend.
6. Ejecutar reindexado si cambiaron documentos.
7. Revisar `/health`.
8. Probar una pregunta en el chat.
