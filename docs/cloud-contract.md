# Contrato cloud

Este documento define como AGROJ ESPECIALIZADO organiza documentos, indices y estado operativo cuando corre en Google Cloud.

## Objetivo

Separar la logica RAG del almacenamiento local. El backend debe poder funcionar con:

- documentos locales durante desarrollo
- documentos en Cloud Storage durante despliegue
- indices locales durante pruebas
- indices publicados en Cloud Storage en produccion
- metadatos en Firestore cuando se opera en cloud

## Backends soportados

```text
DOCUMENT_STORAGE_BACKEND=local|gcs
INDEX_STORAGE_BACKEND=local|gcs
METADATA_BACKEND=none|firestore
PROCESS_STATE_BACKEND=none|firestore
```

## Repositorios del backend

| Archivo | Responsabilidad |
| --- | --- |
| `document_repository.py` | Lee documentos desde disco local o GCS. |
| `index_repository.py` | Lee y publica indices en local o GCS. |
| `metadata_repository.py` | Guarda documentos, jobs y runtime state. |
| `cloud_layout.py` | Centraliza nombres de buckets, prefijos y rutas cloud. |
| `index_models.py` | Define manifiestos, releases y referencias de indice. |
| `metadata_models.py` | Define modelos documentales y de proceso. |

## Cloud Storage

### Bucket de documentos

```text
gs://tesis-producto-dev-documents/documents/
```

Uso:

- guardar PDFs originales
- conservar rutas relativas
- permitir subida directa de archivos grandes

Ejemplo:

```text
documents/manual-papa.pdf
documents/agroecologia/guia-suelos.pdf
```

### Bucket de indices

```text
gs://tesis-producto-dev-indexes/indexes/
```

Uso:

- guardar indice activo
- guardar releases historicos
- guardar manifiesto
- guardar chunk cache
- guardar archivos persistidos de LlamaIndex

Layout recomendado:

```text
indexes/
  active-index.json
  current/
    manifest.json
    chunk_cache.json
    docstore.json
    index_store.json
    default__vector_store.json
  releases/
    20260728-143044/
      manifest.json
      chunk_cache.json
      ...
```

## Indice activo

El backend no debe depender de un release escrito a mano. Debe leer un puntero estable:

```text
indexes/active-index.json
```

Ese puntero indica:

- nombre del indice activo
- ubicacion del manifiesto
- ubicacion del chunk cache
- prefijo de artefactos
- fecha de actualizacion
- origen del indice

## Manifest

El manifiesto resume que documentos forman parte del indice.

Campos principales:

```text
manifest_version
embed_model
files[]
```

Por cada archivo:

```text
file_name
relative_path
size
fingerprint
```

Uso:

- detectar cambios reales
- saber si un PDF ya esta indexado
- evitar rebuilds innecesarios
- mantener trazabilidad entre documentos e indice

## Chunk cache

El chunk cache guarda fragmentos procesados.

Cada fragmento puede incluir:

```text
file_name
page_label
text
tokens[]
topics[]
entities[]
key_terms[]
```

Uso:

- acelerar consultas
- permitir fallback lexical
- exponer fuentes
- reconstruir contexto sin releer todo el PDF

## Firestore

### Coleccion `documents`

Un registro por documento.

Campos frecuentes:

```text
document_id
file_name
relative_path
storage_path
fingerprint
size
status
topics
entities
key_terms
created_at
updated_at
```

Estados:

```text
pending_index
indexed
failed
deleted
```

### Coleccion `reindex_jobs`

Un registro por ejecucion de reindexado.

Campos frecuentes:

```text
job_id
trigger
status
started_at
finished_at
release_name
error_message
total_documents
processed_documents
progress
```

### Coleccion `runtime_state`

Estado operativo compartido.

Campos frecuentes:

```text
active_index
last_reindex_status
last_reindex_job_id
reindex_progress
reindex_stage
reindex_detail
frequent_questions
last_generation_status
```

## Reindexado

El entrypoint batch es:

```powershell
python -m app.reindex_job
```

Responsabilidades:

1. leer PDFs desde el backend documental configurado
2. extraer texto
3. dividir en fragmentos
4. generar embeddings
5. construir indice
6. publicar artefactos
7. actualizar Firestore
8. marcar indice activo

## Reglas de consistencia

- Si un PDF cambia, debe quedar como `pending_index`.
- Si el reindexado termina bien, debe quedar como `indexed`.
- Si falla lectura o analisis, debe quedar como `failed`.
- El backend web no debe reconstruir indices pesados en vivo.
- El job es la fuente confiable para publicar un indice nuevo.

## Limpieza y seguridad

- No subir secretos a Git.
- No versionar indices generados.
- No empaquetar PDFs dentro de la imagen Docker.
- No depender de `backend/storage/` en Cloud Run.
- Usar Secret Manager para claves sensibles.
