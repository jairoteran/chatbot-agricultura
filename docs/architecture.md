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

### Panel de gestion documental

- vive dentro del frontend en la ruta `/gestion`
- usa Google Sign-In para autenticar cuentas concretas
- el backend valida el `credential` de Google y entrega una sesion de gestion documental propia
- el acceso queda restringido a cuentas autorizadas mediante `ADMIN_EMAILS`
- desde esta vista se permite:
  - listar documentos del corpus
  - subir PDFs manualmente
  - eliminar PDFs
  - disparar reindexado manual

### Gobernanza documental actual y evolucion recomendada

Estado actual:

- el acceso operativo se controla mediante Google Sign-In y `ADMIN_EMAILS`
- el sistema funciona con una lista blanca de cuentas autorizadas
- no se presenta como una jerarquia de roles, sino como acceso autorizado a la gestion del corpus
- tecnicamente eso resuelve autenticacion y operacion documental basica

Evolucion recomendada:

- evitar depender conceptualmente de un unico `administrador` o de roles rigidos
- separar el flujo documental en etapas como:
  - `subido`
  - `en revision`
  - `aprobado`
  - `rechazado`
  - `indexado`
- permitir en una fase futura perfiles como:
  - `colaborador`: sube documentos
  - `revisor`: valida o rechaza
  - `curador` o `gestor`: aprueba e incorpora al corpus indexado
- si se implementan permisos futuros, priorizar permisos por accion antes que etiquetas rigidas de rol

Motivo:

- mejora la gobernanza del conocimiento
- reduce centralizacion operativa
- representa mejor un flujo academico o comunitario de validacion de saberes
- fortalece la justificacion metodologica de la tesis

### Politica de reindexado

- el backend HTTP ya no reindexa automaticamente cuando detecta cambios en los PDFs
- si detecta diferencias entre manifiesto actual e indice publicado, marca el estado como `pendiente`
- la reconstruccion del indice se ejecuta solo por accion manual:
  - desde `POST /reindex`
  - o desde el Cloud Run Job batch
- esto evita que la API web se comporte como un proceso pesado de rebuild durante consultas normales

### Modelo NLP realmente utilizado

El proyecto no usa un unico modelo NLP, sino una arquitectura `RAG` con dos capas principales:

- `Gemini 2.5 Flash`:
  - genera la respuesta final en lenguaje natural
  - interpreta la pregunta del usuario
  - redacta respuestas y resumenes a partir del contexto recuperado
- `sentence-transformers/all-MiniLM-L6-v2`:
  - genera embeddings semanticos de los documentos
  - permite recuperar fragmentos relevantes por similitud
  - se integra mediante `Hugging Face` y `llama-index`

Interpretacion correcta para tesis o defensa:

- el modelo de generacion principal es `Gemini 2.5 Flash`
- el modelo de recuperacion semantica principal es `all-MiniLM-L6-v2`
- por tanto, el sistema usa una arquitectura NLP hibrida, no un solo modelo aislado

### Papel de Hugging Face, spaCy y NLTK

- `Hugging Face`:
  - ya participa en el proyecto mediante `sentence-transformers`
  - hoy se usa para embeddings y recuperacion semantica, no como chatbot principal
- `spaCy`:
  - queda integrado como capa de enriquecimiento del corpus durante el reindexado
  - extrae temas, entidades y terminos clave para registrar metadatos documentales
  - si no existe un modelo entrenado de espanol instalado, el sistema usa un fallback ligero con vocabulario de dominio para no romper local ni cloud
- `NLTK`:
  - no esta integrado actualmente
  - se mantiene fuera del runtime porque la limpieza/tokenizacion actual ya queda cubierta por spaCy, reglas propias y el pipeline RAG
  - podria evaluarse despues solo si se necesita un recurso puntual de tokenizacion, stopwords o validacion linguistica

### Corpus documental

En este proyecto, el `corpus` es el conjunto organizado de documentos PDF que alimenta al sistema.

Ese corpus:

- contiene manuales, textos tecnicos, documentos historicos y materiales sobre agricultura y saberes ancestrales
- se almacena en `Cloud Storage`
- se registra en `Firestore` mediante metadatos y estado
- se transforma en un indice consultable mediante el proceso de reindexado
- registra estados documentales como `pending_index`, `indexed`, `deleted` y `failed`
- puede guardar temas, entidades y terminos clave extraidos con `spaCy` o con el fallback de dominio

Desde la perspectiva academica, esto permite describir el sistema no solo como un chatbot con PDFs, sino como un asistente construido sobre un corpus documental especializado.

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
- Atender `chat`, `health` y futuras operaciones de gestion documental
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
- `GEMINI_FALLBACK_MODEL` no es secreto, pero permite definir un segundo modelo Gemini para contingencias de alta demanda

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
- `ENABLE_VECTOR_RETRIEVAL`
- `GEMINI_MODEL`
- `GEMINI_FALLBACK_MODEL`
- `LLM_TIMEOUT_SECONDS`
- `GOOGLE_AUTH_CLIENT_ID`
- `ADMIN_EMAILS`
- `ADMIN_BASE_PATH`
- `ADMIN_SESSION_TTL_SECONDS`

## Flujo objetivo de reindexado

1. Un documento nuevo o actualizado se registra en el sistema.
2. El PDF se guarda en Cloud Storage.
3. Se crea o actualiza un registro de documento en Firestore.
4. El sistema queda marcado como pendiente de reindexado.
5. Una cuenta autorizada ejecuta manualmente el reindexado desde el panel de gestion documental o mediante Cloud Run Job.
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

El reindexado del entorno desplegado debe ser manual y controlado desde gestion documental.

Motivo:

- reduce riesgo de rebuild pesado durante trafico normal
- hace mas predecible el estado del indice
- separa claramente consultas publicas de operaciones operativas

Nota operativa:

- `ALLOW_RUNTIME_REINDEX=false` evita reconstrucciones dentro de la API web
- `ENABLE_VECTOR_RETRIEVAL=true` permite que la API cargue el indice vectorial publicado y responda de forma mas parecida al entorno local
- estas dos decisiones deben mantenerse separadas para no degradar cloud a `lexical-only`

### Decision 6

La UI del acceso de gestion documental puede usar una capa visual propia, pero el click real debe seguir pasando por Google Identity Services.

Motivo:

- permite respetar el estilo visual del panel
- evita romper el flujo real de autenticacion con intentos custom que no abren correctamente el acceso de Google

### Decision 7

El sistema debe describirse como una arquitectura `RAG` basada en corpus, no como un chatbot generativo aislado.

Motivo:

- refleja mejor la realidad tecnica del proyecto
- aclara que las respuestas dependen de documentos recuperados
- permite justificar de forma correcta el uso combinado de Gemini y embeddings de Hugging Face

### Decision 8

La evolucion futura de la gestion documental debe priorizar flujo de curacion antes que un rol unico de administrador.

Motivo:

- mejora trazabilidad y validacion de contenidos
- es mas coherente con un proyecto sobre saberes ancestrales
- abre camino a estados documentales y revision colaborativa

### Decision 9

La interfaz visible debe hablar de `gestion documental` y `cuentas autorizadas`, no de un rol central de administrador.

Motivo:

- alinea el producto con la recomendacion metodologica de evitar roles rigidos
- mantiene el control operativo necesario para proteger el corpus
- permite explicar el sistema como gobernanza documental basada en acceso autorizado
- deja los nombres tecnicos internos como `admin` solo por compatibilidad de endpoints y configuracion existente

## Evolucion prevista

Cuando el producto necesite modelos de datos relacionales mas complejos, reportes, multiusuario avanzado o consistencia transaccional mas rica, evaluar migracion parcial o total de metadatos a `Cloud SQL PostgreSQL`.

## Fuera de alcance por ahora

- Kubernetes / GKE
- microservicios separados por dominio
- autenticacion completa
- multi-tenant
- pipeline CI/CD completo de produccion
