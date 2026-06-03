# Cloud Run y Cloud Run Jobs

## Objetivo

Preparar una sola imagen de contenedor reutilizable para:

- `Cloud Run` como API HTTP
- `Cloud Run Jobs` como proceso batch de reindexado

## Imagen actual

Archivo:

- `backend/Dockerfile`
- `backend/.dockerignore`
- `backend/cloudrun.env.yaml.example`
- `backend/cloudbuild.backend.yaml`

La imagen actual:

- instala dependencias del backend
- copia `app/`
- copia `storage/`
- arranca por defecto la API con `uvicorn`

Nota:

- ahora la imagen ya no copia `backend/data/`
- el backend cloud asume que los documentos viven en `Cloud Storage`

## Uso previsto

### Cloud Run service

La API usa el comando por defecto del contenedor:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Cloud Run Job

El job debe sobrescribir el comando para ejecutar:

```text
python -m app.reindex_job
```

## Estado actual

La imagen ya sirve para pruebas y despliegue inicial.

Supuestos actuales:

- `INDEX_STORAGE_BACKEND=gcs`
- `METADATA_BACKEND=firestore`
- `PROCESS_STATE_BACKEND=firestore`
- `DOCUMENT_STORAGE_BACKEND=gcs`

Implicacion:

- la API y el Cloud Run Job toman los PDFs desde el bucket `tesis-producto-dev-documents`
- `backend/data/` ya queda como respaldo local para desarrollo fuera de Cloud Run

## Variables de entorno minimas

Para Cloud Run service y Cloud Run Jobs:

- `APP_DEPLOYMENT_TARGET=cloud-run`
- `DOCUMENT_STORAGE_BACKEND=gcs`
- `INDEX_STORAGE_BACKEND=gcs`
- `METADATA_BACKEND=firestore`
- `PROCESS_STATE_BACKEND=firestore`
- `GOOGLE_CLOUD_PROJECT=project-838503ae-99e5-4041-837`
- `GOOGLE_CLOUD_REGION=us-central1`
- `DOCUMENTS_BUCKET=tesis-producto-dev-documents`
- `DOCUMENTS_PREFIX=documents`
- `INDEXES_BUCKET=tesis-producto-dev-indexes`
- `INDEXES_PREFIX=indexes`
- `ACTIVE_INDEX_NAME=current`
- `FIRESTORE_DOCUMENTS_COLLECTION=documents`
- `FIRESTORE_JOBS_COLLECTION=reindex_jobs`
- `FIRESTORE_RUNTIME_COLLECTION=runtime_state`
- `ALLOW_RUNTIME_REINDEX="true"`

Ademas, para respuestas generativas:

- `GEMINI_API_KEY`
- `GEMINI_MODEL=gemini-2.5-flash`

## Comandos orientativos

### Construir imagen

Desde la raiz del proyecto:

```powershell
gcloud builds submit . --config backend/cloudbuild.backend.yaml --substitutions _IMAGE=us-central1-docker.pkg.dev/project-838503ae-99e5-4041-837/tesis-producto/backend:latest
```

Script auxiliar del repo:

```powershell
.\scripts\build-backend-image.ps1
```

## Desplegar API en Cloud Run

```powershell
gcloud run deploy tesis-producto-api `
  --image us-central1-docker.pkg.dev/project-838503ae-99e5-4041-837/tesis-producto/backend:latest `
  --region us-central1 `
  --platform managed `
  --allow-unauthenticated
```

Script auxiliar del repo:

```powershell
.\scripts\deploy-backend-api.ps1
```

El script despliega la API con `1Gi` de memoria por defecto, porque `512Mi` resulto insuficiente durante la inicializacion real del servicio en Cloud Run.
Ademas, el script fuerza `ALLOW_RUNTIME_REINDEX=false` para la API cloud, de modo que el servicio web no intente reindexar ni cargar el backend pesado de embeddings en vivo como si fuera el job batch.
El retrieval vectorial de la API se controla aparte con `ENABLE_VECTOR_RETRIEVAL=true`; esa variable permite cargar el indice vectorial publicado sin permitir rebuilds dentro del servicio web.

Con el bloque de gestion documental actual tambien debes asegurar:

- `GOOGLE_AUTH_CLIENT_ID` configurado en `backend/cloudrun.env.yaml` o pasado al script
- `ADMIN_EMAILS` con la lista de correos autorizados
- `ADMIN_SESSION_SECRET` disponible desde Secret Manager si vas a usar acceso protegido en cloud
- `ENABLE_VECTOR_RETRIEVAL=true` si quieres que cloud recupere fragmentos con el indice vectorial igual que local

Si ya tienes un secreto creado en Secret Manager para Gemini:

```powershell
.\scripts\deploy-backend-api.ps1 -GeminiApiSecret GEMINI_API_KEY
```

Si quieres desplegar ya con documentos en `GCS`:

```powershell
.\scripts\deploy-backend-api.ps1 -GeminiApiSecret GEMINI_API_KEY -DocumentStorageBackend gcs
```

## Crear Cloud Run Job

```powershell
gcloud run jobs create tesis-producto-reindex `
  --image us-central1-docker.pkg.dev/project-838503ae-99e5-4041-837/tesis-producto/backend:latest `
  --region us-central1 `
  --command python `
  --args=-m,app.reindex_job
```

Script auxiliar del repo:

```powershell
Copy-Item backend\cloudrun.env.yaml.example backend\cloudrun.env.yaml
.\scripts\deploy-reindex-job.ps1
```

Si el job ya debe leer los PDFs desde el bucket:

```powershell
.\scripts\deploy-reindex-job.ps1 -DocumentStorageBackend gcs
```

El script del job ahora despliega con `2Gi` de memoria por defecto, porque `512Mi` resulto insuficiente para el reindexado real con documentos en `GCS` y reconstruccion de embeddings/indice.
Tambien despliega con `2 vCPU` y `60m` de `task timeout` por defecto, porque `1 vCPU` y `10m` resultaron insuficientes para el rebuild completo leyendo documentos desde `GCS`.

## Ejecutar Cloud Run Job

```powershell
gcloud run jobs execute tesis-producto-reindex --region us-central1
```

Si quieres crear o actualizar el job y ejecutarlo enseguida:

```powershell
.\scripts\deploy-reindex-job.ps1 -ExecuteNow
```

## Operacion manual desde el panel de gestion documental

Con la version actual del proyecto:

- subir o eliminar PDFs desde `/gestion` ya no dispara reindexado automatico
- el backend marca el indice como pendiente cuando detecta cambios
- una cuenta autorizada debe ejecutar manualmente `Reindexar ahora` desde el panel
- como alternativa operativa, tambien puede ejecutarse el Cloud Run Job `tesis-producto-reindex`

Esto deja el flujo cloud alineado con la decision de no reconstruir el indice durante trafico normal de la API web.

## Frontend en Firebase Hosting

La arquitectura objetivo de este repo deja el frontend en `Firebase Hosting` y mantiene el backend HTTP en `Cloud Run`.

Configuracion incluida en la raiz del repo:

- `firebase.json`
- `.firebaserc`
- `scripts/deploy-frontend-hosting.ps1`

La estrategia usada es:

- servir `frontend/dist` como sitio estatico
- reescribir `/api/**` hacia `tesis-producto-api` en `us-central1`

Eso permite que el frontend publicado siga usando rutas relativas como `/api/chat` y evita configurar `CORS` para un dominio frontend separado.

Despliegue:

```powershell
.\scripts\deploy-frontend-hosting.ps1
```

## Secretos

En esta fase, el archivo `backend/cloudrun.env.yaml` no incluye secretos.

Siguiente mejora recomendada:

- mover `GEMINI_API_KEY` a Secret Manager
- pasar el secreto al servicio/job con `--set-secrets`

Para la API en Cloud Run ya quedo preparado el script `scripts/deploy-backend-api.ps1` para aceptar:

- `-GeminiApiSecret GEMINI_API_KEY`

Tambien se agrego un script auxiliar para crear o actualizar el secreto:

```powershell
.\scripts\set-gemini-secret.ps1 -SecretValue "TU_CLAVE_REAL"
```

Y luego desplegar la API usando ese secreto:

```powershell
.\scripts\deploy-backend-api.ps1 -GeminiApiSecret GEMINI_API_KEY
```

Mientras eso no este hecho, no versionar un archivo `cloudrun.env.yaml` con claves reales.

## Siguiente mejora prevista

La siguiente evolucion natural es:

1. subir los PDFs con `scripts/sync-documents-to-gcs.ps1`
2. desplegar el job con `-DocumentStorageBackend gcs`
3. ejecutar un reindexado cloud contra los documentos del bucket
4. desplegar la API con `-DocumentStorageBackend gcs`
5. mantener la imagen sin `backend/data/` embebido y usar `backend/data/` solo para trabajo local

## Migracion recomendada de documentos

Orden sugerido para cambiar a documentos cloud sin romper la API:

1. subir los PDFs actuales al bucket

```powershell
.\scripts\sync-documents-to-gcs.ps1
```

Si quieres limpiar del bucket archivos viejos que no sean PDFs sincronizados por el script:

```powershell
.\scripts\sync-documents-to-gcs.ps1 -DeleteUnmatchedDestinationObjects
```

2. actualizar el Cloud Run Job para que tome los documentos desde `GCS`

```powershell
.\scripts\deploy-reindex-job.ps1 -DocumentStorageBackend gcs
```

3. ejecutar el job de reindexado

```powershell
gcloud run jobs execute tesis-producto-reindex --region us-central1
```

4. desplegar la API usando tambien `DOCUMENT_STORAGE_BACKEND=gcs`

```powershell
.\scripts\deploy-backend-api.ps1 -GeminiApiSecret GEMINI_API_KEY -DocumentStorageBackend gcs
```

5. validar `/health` y luego probar consultas reales
