# Contrato cloud del backend

## Objetivo

Definir una estructura estable para que el backend pueda migrar desde archivos locales a Google Cloud sin rehacer toda la logica RAG.

## Backends previstos

- `DOCUMENT_STORAGE_BACKEND=local|gcs`
- `INDEX_STORAGE_BACKEND=local|gcs`
- `METADATA_BACKEND=none|firestore`
- `PROCESS_STATE_BACKEND=none|firestore`

## Contratos implementados en codigo

Archivos relevantes:

- `backend/app/settings.py`
- `backend/app/index_models.py`
- `backend/app/cloud_layout.py`
- `backend/app/index_repository.py`

## Repositorio de indices

Ya existe una capa de repositorio para indices:

- `LocalIndexRepository`
- `GCSIndexRepository`

Objetivo:

- que el servicio RAG deje de depender de leer siempre desde `backend/storage/`
- permitir que el indice activo se materialice en un directorio local temporal aunque su origen sea Cloud Storage
- reutilizar el mismo contrato de manifiesto y chunk cache en local y en cloud

## Repositorio de metadatos

Ya existe una capa de metadatos y estado:

- `NoopMetadataRepository`
- `FirestoreMetadataRepository`

Modelos implementados:

- `DocumentRecord`
- `ReindexJobRecord`
- `RuntimeStateRecord`

Objetivo:

- registrar documentos indexados
- registrar jobs de reindexado
- mantener estado runtime del indice activo
- permitir que `/health` refleje estado operativo mas alla del filesystem local

## Entry point batch

Ya existe un entrypoint batch para reindexado:

- `python -m app.reindex_job`

Objetivo:

- ejecutar reindexado sin levantar `uvicorn`
- reutilizar exactamente el mismo `RAGService`
- preparar el camino para `Cloud Run Jobs`

## Directorio de cache cloud

Cuando el backend use `INDEX_STORAGE_BACKEND=gcs`, la sincronizacion del indice activo se hace sobre un cache local configurable:

- `CLOUD_INDEX_CACHE_DIR`

Uso previsto:

- descargar `active-index.json`
- descargar `manifest.json`
- descargar `chunk_cache.json`
- descargar los archivos persistidos del indice requeridos por LlamaIndex

## Modelos de indice

### IndexManifest

Representa el conjunto de documentos que forman un indice:

- `manifest_version`
- `embed_model`
- `files[]`

Cada archivo indexado guarda:

- `file_name`
- `relative_path`
- `size`
- `fingerprint`

## Chunk cache

Cada fragmento serializado guarda:

- `file_name`
- `page_label`
- `text`
- `tokens[]`

Eso permite mantener compatibilidad con el flujo actual y luego mover el almacenamiento a Cloud Storage.

## Layout sugerido en Cloud Storage

Bucket de documentos:

- `documents/<relative_path_del_pdf>`

Bucket o prefijo de indices:

- `indexes/active-index.json`
- `indexes/current/`
- `indexes/releases/<release_id>/manifest.json`
- `indexes/releases/<release_id>/chunk_cache.json`

## Idea del indice activo

La referencia estable para la API no debe depender de un release hardcodeado. La API deberia leer un puntero estable, por ejemplo:

- `indexes/active-index.json`

Ese puntero deberia indicar:

- nombre del indice activo
- ubicacion del `manifest.json`
- ubicacion del `chunk_cache.json`
- prefijo de storage del release
- timestamp de actualizacion

## Contrato Firestore sugerido

### Coleccion `documents`

Un registro por PDF:

- `document_id`
- `file_name`
- `relative_path`
- `storage_path`
- `fingerprint`
- `status`
- `created_at`
- `updated_at`

### Coleccion `reindex_jobs`

Un registro por job:

- `job_id`
- `trigger`
- `status`
- `started_at`
- `finished_at`
- `release_name`
- `error_message`

### Coleccion `runtime_state`

Estado operativo compartido:

- `active_index`
- `last_successful_reindex`
- `last_failed_reindex`
- `last_reindex_status`
- `last_reindex_job_id`

## Siguiente implementacion natural

1. Adaptar el backend para leer y escribir este contrato en `local` o `gcs`
2. Definir un repositorio para metadatos `none|firestore`
3. Preparar el proceso de reindexado para publicar releases y actualizar el puntero activo
