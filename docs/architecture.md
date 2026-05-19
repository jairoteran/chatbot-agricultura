# Arquitectura objetivo

## Objetivo actual

Migrar el proyecto desde un enfoque basado en archivos locales versionados en Git hacia una arquitectura administrada en Google Cloud que soporte crecimiento, reindexado en vivo y mejor separacion de responsabilidades.

## Arquitectura recomendada hoy

- `Frontend`: Firebase Hosting
- `Backend API`: Cloud Run
- `Reindexado`: Cloud Run Jobs
- `PDFs`: Cloud Storage
- `Indices`: Cloud Storage
- `Estado de documentos`: Firestore
- `Estado de procesos`: Firestore
- `Secrets`: Secret Manager

## Convencion de nombres recomendada

Base sugerida del proyecto:

- `project_slug`: `tesis-producto`
- `environment`: `dev`, `staging`, `prod`
- `region`: `us-central1` mientras usemos bien el trial y el free tier cercano

Recursos sugeridos para `dev`:

- `documents bucket`: `tesis-producto-dev-documents`
- `indexes bucket`: `tesis-producto-dev-indexes`
- `active index alias`: `current`
- `Firestore documents collection`: `documents`
- `Firestore jobs collection`: `reindex_jobs`
- `Firestore runtime collection`: `runtime_state`

Prefijos sugeridos en Cloud Storage:

- `documents/`
- `indexes/current/`
- `indexes/releases/`

## Responsabilidad por servicio

### Panel administrativo

- vive dentro del frontend en la ruta `/gestion`
- usa Google Sign-In para autenticar cuentas concretas
- el backend valida el `credential` de Google y entrega una sesion administrativa propia
- el acceso queda restringido por `ADMIN_EMAILS`
- desde esta vista se permite:
  - listar documentos administrables
  - subir PDFs manualmente
  - eliminar PDFs
  - disparar reindexado manual

### Politica de reindexado

- el backend HTTP ya no reindexa automaticamente cuando detecta cambios en los PDFs
- si detecta diferencias entre manifiesto actual e indice publicado, marca el estado como `pendiente`
- la reconstruccion del indice se ejecuta solo por accion manual:
  - desde `POST /reindex`
  - o desde el Cloud Run Job batch
- esto evita que la API web se comporte como un proceso pesado de rebuild durante consultas normales

### Frontend publico

Opcion ideal:

- `Firebase Hosting`
- servir el frontend React compilado
- exponer el dominio publico del cliente
- reescribir `/api/**` hacia `tesis-producto-api` en `us-central1` para evitar problemas de CORS entre frontend y backend

Opcion operativa alternativa:

- `Cloud Run` sirviendo el frontend estatico compilado
- consumir la API publica de `Cloud Run` por URL completa
- habilitar `CORS_ORIGINS` en la API para el dominio del frontend

### Cloud Run

- Exponer la API HTTP principal
- Atender `chat`, `health` y futuras operaciones de administracion
- Leer configuracion desde Secret Manager
- Consultar Firestore para estado y metadatos
- Leer el indice publicado en almacenamiento duradero
- Mantener compatibilidad local mientras termina la migracion

### Cloud Run Jobs

- Ejecutar el reindexado fuera del ciclo normal de requests HTTP
- Leer PDFs desde Cloud Storage
- Reconstruir o actualizar el indice
- Publicar artefactos nuevos del indice en Cloud Storage
- Reportar progreso y resultado en Firestore
- Reutilizar el entrypoint batch del backend en lugar de depender de FastAPI

### Cloud Storage

- Bucket para documentos PDF
- Bucket o prefijo para artefactos del indice
- Posible separacion futura entre entornos `dev`, `staging` y `prod`
- Publicar una referencia estable al indice activo y permitir releases versionados

### Firestore

- Registrar documentos subidos
- Registrar jobs de reindexado
- Guardar estado de proceso, errores y timestamps
- Servir como capa de coordinacion ligera en esta fase

### Secret Manager

- Guardar claves como `GEMINI_API_KEY` y `OPENAI_API_KEY`
- Guardar configuraciones sensibles del backend

## Variables de entorno base

Variables ya previstas en el backend:

- `APP_DEPLOYMENT_TARGET`
- `DOCUMENT_STORAGE_BACKEND`
- `INDEX_STORAGE_BACKEND`
- `METADATA_BACKEND`
- `PROCESS_STATE_BACKEND`
- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_REGION`
- `DOCUMENTS_BUCKET`
- `DOCUMENTS_PREFIX`
- `INDEXES_BUCKET`
- `INDEXES_PREFIX`
- `ACTIVE_INDEX_NAME`
- `FIRESTORE_DOCUMENTS_COLLECTION`
- `FIRESTORE_JOBS_COLLECTION`
- `FIRESTORE_RUNTIME_COLLECTION`
- `ALLOW_RUNTIME_REINDEX`
- `GOOGLE_AUTH_CLIENT_ID`
- `ADMIN_EMAILS`
- `ADMIN_BASE_PATH`
- `ADMIN_SESSION_TTL_SECONDS`

## Flujo objetivo de reindexado

1. Un documento nuevo o actualizado se registra en el sistema.
2. El PDF se guarda en Cloud Storage.
3. Se crea o actualiza un registro de documento en Firestore.
4. El sistema queda marcado como pendiente de reindexado.
5. Un administrador ejecuta manualmente el reindexado desde el panel o mediante Cloud Run Job.
6. El job o endpoint manual lee los PDFs requeridos y genera el indice.
7. El job o endpoint manual publica el nuevo indice en Cloud Storage.
8. El proceso actualiza en Firestore el resultado del reindexado.
9. La API en Cloud Run consume el indice vigente.

## Decisiones tomadas

### Decision 1

Se prioriza arquitectura serverless administrada sobre VPS.

Motivo:

- mejor imagen profesional
- mejor camino de escalado
- menor carga operativa a largo plazo

### Decision 2

El reindexado no debe depender del filesystem local del servicio web.

Motivo:

- Cloud Run es stateless
- el reindexado puede ser pesado
- conviene separar trafico de usuarios y procesamiento batch

### Decision 3

En esta fase se usara Firestore antes que Cloud SQL.

Motivo:

- mejor compatibilidad con el credito inicial y el trial
- menor costo operativo temprano
- suficiente para estado, trazabilidad y coordinacion inicial

### Decision 4

La configuracion de infraestructura debe salir del codigo de dominio y centralizarse en settings.

Motivo:

- facilita migracion por etapas
- reduce acoplamiento a `backend/data` y `backend/storage`
- hace mas clara la diferencia entre local y cloud

### Decision 5

El reindexado del entorno desplegado debe ser manual y controlado desde administracion.

Motivo:

- reduce riesgo de rebuild pesado durante trafico normal
- hace mas predecible el estado del indice
- separa claramente consultas publicas de operaciones operativas

### Decision 6

La UI del login admin puede usar una capa visual propia, pero el click real debe seguir pasando por Google Identity Services.

Motivo:

- permite respetar el estilo visual del panel
- evita romper el flujo real de autenticacion con intentos custom que no abren correctamente el acceso de Google

## Evolucion prevista

Cuando el producto necesite modelos de datos relacionales mas complejos, reportes, multiusuario avanzado o consistencia transaccional mas rica, evaluar migracion parcial o total de metadatos a `Cloud SQL PostgreSQL`.

## Fuera de alcance por ahora

- Kubernetes / GKE
- microservicios separados por dominio
- autenticacion completa
- multi-tenant
- pipeline CI/CD completo de produccion
