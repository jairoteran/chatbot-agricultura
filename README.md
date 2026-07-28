# AGROJ ESPECIALIZADO

AGROJ ESPECIALIZADO es una aplicacion web para consultar informacion agricola a partir de una base documental propia. El usuario conversa con un chat, hace preguntas sobre cultivos, practicas agricolas, agroecologia, territorio rural o saberes ancestrales, y el sistema responde usando documentos PDF previamente cargados e indexados.

El proyecto combina una interfaz web en React, un backend en FastAPI y una arquitectura RAG para buscar fragmentos relevantes dentro de los documentos antes de generar una respuesta natural con IA.

## Que problema resuelve

Muchos documentos tecnicos, historicos y academicos sobre agricultura quedan dispersos en PDFs dificiles de revisar manualmente. AGROJ ESPECIALIZADO organiza esos documentos en una base consultable y permite:

- hacer preguntas en lenguaje natural
- obtener respuestas directas y faciles de leer
- consultar informacion respaldada por fuentes documentales
- subir nuevos documentos desde un panel protegido
- ejecutar reindexado manual cuando cambia la base documental
- mantener una arquitectura lista para operar en Google Cloud

## Como funciona

```text
Usuario
  |
  v
Frontend React / Vite
  |
  v
Backend FastAPI
  |
  v
RAG con LlamaIndex
  |
  +--> Embeddings: sentence-transformers/all-MiniLM-L6-v2
  |
  +--> Busqueda semantica y lexical en fragmentos de documentos
  |
  v
Gemini 2.5 Flash
  |
  v
Respuesta final para el usuario
```

Flujo general:

1. Los documentos PDF se suben al sistema.
2. Los archivos quedan almacenados en Google Cloud Storage.
3. El reindexado lee los PDFs, extrae texto y divide el contenido en fragmentos.
4. Cada fragmento se convierte en embeddings con `sentence-transformers/all-MiniLM-L6-v2`.
5. Cuando el usuario pregunta algo, la pregunta tambien se convierte en una representacion semantica.
6. El sistema busca los fragmentos mas relacionados con la pregunta.
7. Gemini recibe la pregunta y los fragmentos recuperados.
8. El backend devuelve una respuesta clara, conversacional y enfocada en agricultura.

Importante: el proyecto no entrena un modelo propio desde cero. Usa modelos ya entrenados y actualiza el indice documental cuando se agregan o eliminan PDFs.

## Arquitectura principal

```text
frontend/
  React + Vite
  Interfaz publica del chat y panel de gestion documental

backend/
  FastAPI
  Servicio RAG, autenticacion de gestion, subida de documentos y reindexado

scripts/
  Automatizacion de build, deploy, reindexado y sincronizacion con Google Cloud

docs/
  Documentacion tecnica viva del proyecto
```

Servicios usados en Google Cloud:

- `Cloud Run`: publica el backend API y el frontend.
- `Cloud Run Jobs`: ejecuta el reindexado pesado fuera del request web.
- `Cloud Storage`: almacena PDFs originales e indices generados.
- `Firestore`: guarda metadatos de documentos, estado del reindexado y estado operativo.
- `Secret Manager`: protege claves como `GEMINI_API_KEY` y `ADMIN_SESSION_SECRET`.
- `Artifact Registry`: almacena las imagenes Docker del backend y frontend.

## Componentes de IA y NLP

- `LlamaIndex`: framework principal para el flujo RAG.
- `sentence-transformers/all-MiniLM-L6-v2`: modelo de embeddings usado para comparar preguntas y fragmentos.
- `Gemini 2.5 Flash`: modelo generativo que redacta la respuesta final.
- `spaCy`: apoyo para analisis de documentos, extraccion de entidades, temas y terminos clave cuando corresponde.
- `pypdf`: lectura y extraccion de texto desde PDFs.

## Estructura del repositorio

```text
backend/
  app/
    main.py                  # Endpoints FastAPI
    rag_service.py           # Logica RAG, embeddings, recuperacion y respuesta
    document_repository.py   # Lectura de documentos local/GCS
    index_repository.py      # Persistencia de indices local/GCS
    metadata_repository.py   # Metadatos en Firestore o modo local
    corpus_analyzer.py       # Analisis NLP de documentos
  cloudrun.env.yaml          # Variables reales usadas en Cloud Run
  cloudrun.env.yaml.example  # Plantilla de variables cloud
  Dockerfile                 # Imagen del backend

frontend/
  src/
    App.jsx                  # Interfaz principal del chat y panel de gestion
    styles.css               # Estilos de la aplicacion
  Dockerfile                 # Imagen del frontend
  package.json

scripts/
  build-backend-image.ps1
  deploy-backend-api.ps1
  deploy-reindex-job.ps1
  build-frontend-image.ps1
  deploy-frontend-cloudrun.ps1
  sync-documents-to-gcs.ps1
  reindex-local.ps1

docs/
  architecture.md
  cloud-contract.md
  cloud-run-jobs.md
  evidence-log.md
  glossary.md
  project-status.md
```

## Desarrollo local

Requisitos recomendados:

- Python 3.12
- Node.js 20 o superior
- PowerShell
- Google Cloud CLI, si vas a trabajar con Cloud

### Backend local

```powershell
cd "C:\Users\Jairo Teran\Downloads\Tesis\Producto\backend"

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
pip install -r requirements.indexing.txt

.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Endpoint de salud:

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/health" |
  ConvertTo-Json -Depth 10
```

### Frontend local

En otra terminal:

```powershell
cd "C:\Users\Jairo Teran\Downloads\Tesis\Producto\frontend"

npm install
npm run dev
```

URL local:

```text
http://localhost:5173
```

El frontend usa el proxy de Vite para hablar con el backend local en `127.0.0.1:8000`.

### Inicio rapido desde la raiz

```powershell
cd "C:\Users\Jairo Teran\Downloads\Tesis\Producto"
.\start-all.ps1
```

## Variables importantes

Variables principales del backend:

```text
APP_DEPLOYMENT_TARGET=cloud-run
DOCUMENT_STORAGE_BACKEND=gcs
INDEX_STORAGE_BACKEND=gcs
METADATA_BACKEND=firestore
PROCESS_STATE_BACKEND=firestore
DOCUMENTS_BUCKET=tesis-producto-dev-documents
INDEXES_BUCKET=tesis-producto-dev-indexes
ACTIVE_INDEX_NAME=current
ALLOW_RUNTIME_REINDEX=false
ENABLE_VECTOR_RETRIEVAL=true
GEMINI_MODEL=gemini-2.5-flash
GEMINI_FALLBACK_MODEL=gemini-2.5-flash-lite
LLM_TIMEOUT_SECONDS=10.0
```

Secretos esperados en Google Secret Manager:

```text
GEMINI_API_KEY
ADMIN_SESSION_SECRET
```

El archivo real para Cloud Run es:

```text
backend/cloudrun.env.yaml
```

La plantilla segura para documentacion es:

```text
backend/cloudrun.env.yaml.example
```

## Gestion documental

El panel protegido vive en:

```text
/gestion
```

Desde ese panel se puede:

- iniciar sesion con Google
- subir PDFs
- listar documentos disponibles
- revisar estados de indexacion
- eliminar documentos
- lanzar reindexado manual
- monitorear progreso del reindexado

La autorizacion se controla con correos permitidos en `ADMIN_EMAILS`.

## Subida masiva de documentos

Para muchos PDFs, la ruta recomendada es subir directo a Cloud Storage y luego ejecutar reindexado.

Ejemplo:

```powershell
gcloud storage cp "C:\ruta\a\documentos\*.pdf" `
  gs://tesis-producto-dev-documents/documents/
```

Si hay subcarpetas:

```powershell
gcloud storage cp "C:\ruta\a\documentos\**" `
  gs://tesis-producto-dev-documents/documents/ `
  --recursive
```

Despues se ejecuta el job:

```powershell
gcloud run jobs execute tesis-producto-reindex `
  --region us-central1
```

Para un paquete grande se recomienda ampliar recursos del job:

```powershell
.\scripts\deploy-reindex-job.ps1 `
  -DocumentStorageBackend gcs `
  -Memory "8Gi" `
  -Cpu "4" `
  -TaskTimeout "43200s"
```

## Despliegue en Google Cloud

Desde la raiz del proyecto:

```powershell
cd "C:\Users\Jairo Teran\Downloads\Tesis\Producto"
```

### Backend

```powershell
.\scripts\build-backend-image.ps1

.\scripts\deploy-backend-api.ps1 `
  -GeminiApiSecret GEMINI_API_KEY `
  -AdminSessionSecret ADMIN_SESSION_SECRET `
  -DocumentStorageBackend gcs `
  -AllowRuntimeReindex "false" `
  -Memory "4Gi" `
  -Cpu "4" `
  -Timeout "120s"
```

### Job de reindexado

```powershell
.\scripts\deploy-reindex-job.ps1 `
  -DocumentStorageBackend gcs `
  -Memory "4Gi" `
  -Cpu "4" `
  -TaskTimeout "60m"
```

Para ejecutarlo:

```powershell
gcloud run jobs execute tesis-producto-reindex `
  --region us-central1
```

### Frontend

```powershell
.\scripts\build-frontend-image.ps1 `
  -ApiBaseUrl "/api" `
  -AdminBasePath "/gestion"

.\scripts\deploy-frontend-cloudrun.ps1
```

## Monitoreo

Ver estado general del backend:

```powershell
Invoke-RestMethod -Method Get `
  -Uri "https://tesis-producto-api-1025954944056.us-central1.run.app/health" |
  ConvertTo-Json -Depth 10
```

Ver ejecuciones del job:

```powershell
gcloud run jobs executions list `
  --job tesis-producto-reindex `
  --region us-central1
```

Ver detalle de una ejecucion:

```powershell
gcloud run jobs executions describe tesis-producto-reindex-XXXXX `
  --region us-central1
```

## Endpoints principales

```text
GET  /health
POST /chat
POST /summarize-document
POST /reindex
GET  /admin/config
GET  /admin/session
POST /admin/session/google
GET  /admin/documents
POST /admin/documents/upload-session
POST /admin/documents/complete
DELETE /admin/documents/{document_id}
```

En desarrollo local, el frontend consume estos endpoints con prefijo `/api` mediante el proxy de Vite.

## Limpieza del repositorio

El repositorio busca mantenerse limpio para facilitar colaboracion y entrega formal:

- `backend/storage/` no se versiona porque contiene indices y caches generados.
- `backend/data/agricultura_tungurahua.pdf` se ignora como archivo de prueba local.
- `frontend/dist/` no se versiona porque se genera con `npm run build`.
- `frontend/node_modules/` no se versiona.
- `.venv/`, `__pycache__/`, logs y archivos temporales quedan ignorados.
- `.gcloudignore` evita subir PDFs, indices y caches al contexto de Cloud Build.

## Documentacion complementaria

- [docs/architecture.md](docs/architecture.md): arquitectura y decisiones tecnicas.
- [docs/cloud-contract.md](docs/cloud-contract.md): contrato cloud para documentos, indices y estado.
- [docs/cloud-run-jobs.md](docs/cloud-run-jobs.md): operacion de Cloud Run Jobs.
- [docs/evidence-log.md](docs/evidence-log.md): registro de avances, errores y evidencia.
- [docs/glossary.md](docs/glossary.md): glosario tecnico del proyecto.
- [docs/project-status.md](docs/project-status.md): estado actual y siguientes pasos.

## Guia para nuevos colaboradores

1. Lee este README completo.
2. Levanta primero el backend local y revisa `/health`.
3. Levanta el frontend local y prueba una pregunta simple.
4. Revisa `backend/app/rag_service.py` para entender el flujo RAG.
5. Revisa `frontend/src/App.jsx` para entender la UI publica y el panel `/gestion`.
6. Antes de tocar despliegues, revisa `scripts/` y `docs/cloud-run-jobs.md`.
7. Si cambias arquitectura, flujos de documentos o despliegue, actualiza `docs/project-status.md` y `docs/evidence-log.md`.

## Estado recomendado antes de hacer commit

```powershell
git status --short
npm --prefix frontend run build
```

Si el cambio toca backend, tambien conviene validar:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

El objetivo del repositorio es que cualquier persona pueda entender que hace el sistema, levantarlo localmente, operar el despliegue cloud y continuar el trabajo sin depender de memoria oral del proyecto.
