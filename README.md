# PDF Chat App

Aplicacion web para consultar documentos PDF con una interfaz de chat. El proyecto usa un frontend en React y un backend en FastAPI con capacidades RAG para recuperar, resumir y explicar informacion de los documentos.

## Estado actual

La arquitectura local actual sigue funcionando con:

- `frontend/`: interfaz web en React + Vite
- `backend/`: API en FastAPI + servicio RAG
- `backend/data/`: PDFs locales de desarrollo
- `backend/storage/`: indice persistido local heredado de la etapa anterior

La siguiente etapa del proyecto migra a una arquitectura en Google Cloud orientada a crecimiento y operacion mas profesional.

## Arquitectura objetivo

La arquitectura recomendada para esta etapa es:

- `Frontend`: Firebase Hosting
- `Backend API`: Cloud Run
- `Reindexado`: Cloud Run Jobs
- `PDFs e indices`: Cloud Storage
- `Estado de documentos y procesos`: Firestore
- `Secrets`: Secret Manager

Documentacion principal:

- [Arquitectura objetivo](docs/architecture.md)
- [Contrato cloud](docs/cloud-contract.md)
- [Estado del proyecto](docs/project-status.md)
- [Guia de documentacion](docs/README.md)

## Estructura del repositorio

```text
api/
backend/
frontend/
scripts/
docs/
```

## Desarrollo local

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Si tambien vas a reconstruir indices localmente durante desarrollo:

```powershell
pip install -r requirements.indexing.txt
```

Para ejecutar el reindexado como proceso batch independiente del servidor web:

```powershell
.venv\Scripts\python -m app.reindex_job
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

## Despliegue del frontend

Hay dos caminos preparados:

- `Firebase Hosting`, si el proyecto tiene permisos y un Hosting site creado
- `Cloud Run`, como alternativa directa cuando ya tienes permisos de despliegue sobre servicios Cloud Run

En el estado actual, el camino mas directo es `Cloud Run`.

Build de imagen:

```powershell
.\scripts\build-frontend-image.ps1
```

Deploy:

```powershell
.\scripts\deploy-frontend-cloudrun.ps1
```

Si el frontend se publica en un dominio distinto al backend, recuerda desplegar la API con `CORS_ORIGINS` incluyendo la URL publica del frontend.

### Inicio rapido desde la raiz

```powershell
.\start-all.ps1
```

## Variables de entorno locales

Backend:

```powershell
$env:GEMINI_API_KEY="tu_clave"
$env:GEMINI_MODEL="gemini-2.5-flash"
```

O alternativamente:

```powershell
$env:OPENAI_API_KEY="tu_clave"
$env:OPENAI_MODEL="gpt-5.4-mini"
```

Frontend opcional:

```env
VITE_API_URL=/api/chat
VITE_HEALTH_URL=/api/health
VITE_REINDEX_URL=/api/reindex
VITE_SUMMARY_URL=/api/summarize-document
```

Puedes partir de:

- `backend/.env.example`
- `frontend/.env.example`

Para la migracion cloud, el backend ya contempla:

- `INDEX_STORAGE_BACKEND=local|gcs`
- `METADATA_BACKEND=none|firestore`
- `PROCESS_STATE_BACKEND=none|firestore`

## Endpoints actuales

- `GET /health`
- `POST /chat`
- `POST /reindex`
- `POST /summarize-document`

## Criterio de documentacion del proyecto

Este repositorio se va a mantener con documentacion viva. Cada cambio importante debe reflejarse al menos en:

- [docs/project-status.md](docs/project-status.md): que se hizo, que falta y bloqueos
- [docs/architecture.md](docs/architecture.md): si cambia la arquitectura objetivo o una decision tecnica importante

La idea es que el repo sea la referencia comun cuando trabajes desde otra computadora o desde GitHub.
