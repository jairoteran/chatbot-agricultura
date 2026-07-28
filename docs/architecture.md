# Arquitectura de AGROJ ESPECIALIZADO

## Vision general

AGROJ ESPECIALIZADO es una aplicacion web de consulta agricola basada en documentos. El sistema no responde desde conocimiento libre del modelo, sino que primero busca evidencia en un corpus de PDFs y luego genera una respuesta natural con IA.

La arquitectura actual esta pensada para operar en Google Cloud, mantener el chat publico disponible y separar las tareas pesadas de reindexado del trafico normal de usuarios.

```text
Usuario
  |
  v
Frontend React / Vite
  |
  v
Backend FastAPI en Cloud Run
  |
  +--> Firestore: metadatos, sesiones y estado
  |
  +--> Cloud Storage: PDFs e indices
  |
  +--> LlamaIndex + embeddings: recuperacion RAG
  |
  v
Gemini 2.5 Flash
  |
  v
Respuesta final
```

## Servicios principales

| Capa | Servicio / Tecnologia | Responsabilidad |
| --- | --- | --- |
| Frontend | React + Vite | Interfaz del chat y panel `/gestion`. |
| Backend | FastAPI + Uvicorn | API, autenticacion, RAG, documentos y estado. |
| RAG | LlamaIndex | Fragmentacion, indice y recuperacion de informacion. |
| Embeddings | `all-MiniLM-L6-v2` | Representacion semantica de textos y preguntas. |
| Generacion | Gemini 2.5 Flash | Redaccion de respuestas naturales. |
| Documentos | Cloud Storage | PDFs originales. |
| Indices | Cloud Storage | Artefactos del indice activo y releases. |
| Estado | Firestore | Metadatos, jobs, progreso y estado runtime. |
| Secretos | Secret Manager | Claves de Gemini y secreto de sesion. |
| Batch | Cloud Run Jobs | Reindexado manual fuera de la API web. |

## Flujo RAG

```text
PDFs cargados
  -> extraccion de texto
  -> division en fragmentos
  -> embeddings por fragmento
  -> indice consultable

Pregunta
  -> validacion de dominio agricola
  -> busqueda semantica y lexical
  -> seleccion de evidencia
  -> prompt con contexto
  -> respuesta con Gemini
```

El sistema intenta responder solo cuando encuentra evidencia suficiente. Si la pregunta esta fuera del dominio agricola o no hay soporte claro en documentos, el backend debe responder de forma honesta en lugar de inventar.

## Modelos utilizados

El proyecto no entrena un modelo propio desde cero. Usa modelos ya entrenados:

- `sentence-transformers/all-MiniLM-L6-v2`: convierte fragmentos y preguntas en embeddings.
- `Gemini 2.5 Flash`: redacta respuestas a partir del contexto recuperado.
- `Gemini 2.5 Flash Lite`: fallback configurado para contingencias.
- `spaCy`: apoyo de analisis documental para entidades, temas y terminos clave.

Interpretacion correcta:

- El modelo generativo principal es Gemini.
- El modelo de recuperacion semantica es `all-MiniLM-L6-v2`.
- El framework RAG es LlamaIndex.
- Lo que se actualiza al subir documentos es el indice, no los pesos de un modelo.

## Gestion documental

La ruta protegida es:

```text
/gestion
```

Permite:

- iniciar sesion con Google
- validar acceso contra `ADMIN_EMAILS`
- subir PDFs
- listar documentos
- eliminar documentos
- lanzar reindexado manual
- ver progreso del reindexado

El lenguaje del sistema habla de gestion documental y cuentas autorizadas, no de una jerarquia rigida de administrador. Esto deja abierta una evolucion futura hacia flujos de curacion documental con colaboradores, revisores y validadores.

## Politica de reindexado

Decision vigente:

- La API web no debe reindexar automaticamente.
- Los cambios documentales dejan el indice como pendiente.
- El reindexado se ejecuta manualmente desde `/gestion` o con Cloud Run Jobs.
- El job batch reconstruye el indice y publica el resultado.

Motivo:

- evita que una consulta de usuario dispare procesos pesados
- reduce timeouts en Cloud Run
- permite monitorear progreso real
- hace mas segura la operacion con cientos de PDFs

## Almacenamiento

### Documentos

```text
gs://tesis-producto-dev-documents/documents/
```

Aqui viven los PDFs originales.

### Indices

```text
gs://tesis-producto-dev-indexes/indexes/
```

Aqui viven:

- manifiestos
- chunk cache
- archivos persistidos de LlamaIndex
- puntero del indice activo
- releases historicos

### Metadatos

Firestore guarda:

- documentos registrados
- estados `pending_index`, `indexed`, `failed`, `deleted`
- jobs de reindexado
- progreso del job
- estado runtime del sistema
- preguntas frecuentes calculadas desde uso real

## Variables importantes

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
```

## Frontend

El frontend se construye con React + Vite. Sus responsabilidades son:

- mostrar el chat publico
- mostrar estado del backend
- mantener historial local de conversaciones
- abrir el menu movil
- mostrar `/gestion`
- realizar subida directa a Cloud Storage para PDFs grandes
- consumir endpoints `/api/**`

En Cloud Run, el frontend se sirve como sitio estatico con Nginx y reescribe `/api/**` hacia el backend.

## Backend

El backend FastAPI expone:

- `/health`
- `/chat`
- `/summarize-document`
- `/reindex`
- `/admin/config`
- `/admin/session`
- `/admin/documents`

Responsabilidades principales:

- orquestar RAG
- validar dominio agricola de preguntas
- recuperar fragmentos relevantes
- generar respuestas
- administrar sesiones de gestion documental
- crear sesiones de subida directa a GCS
- lanzar Cloud Run Jobs
- reportar estado operativo

## Estrategia de escalabilidad

Para uso normal, Cloud Run escala el frontend y el backend bajo demanda.

Para procesos pesados, Cloud Run Jobs permite:

- mas memoria
- mas CPU
- timeout largo
- ejecucion independiente del trafico web

Con muchos documentos, el cuello de botella principal no es el chat sino el reindexado. Por eso el reindexado esta separado.

## Limpieza del repositorio

No se versionan:

- `backend/storage/`
- `frontend/dist/`
- `frontend/node_modules/`
- `.venv/`
- caches
- logs
- PDFs de prueba

El codigo fuente queda separado de artefactos generados, algo importante para mantenimiento, colaboracion y proteccion formal del software.

## Evolucion recomendada

Siguientes mejoras naturales:

- curacion documental con estados mas detallados
- roles por accion en lugar de etiquetas rigidas
- OCR para PDFs escaneados
- versionado mas visible de indices
- panel de calidad documental
- metricas de preguntas frecuentes por periodo
- pruebas automatizadas del flujo RAG
