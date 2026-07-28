# Glosario

Este glosario explica los terminos tecnicos del proyecto con un lenguaje practico.

## AGROJ ESPECIALIZADO

Nombre del software. Es un asistente agricola que responde preguntas usando una base documental propia.

## RAG

Significa `Retrieval-Augmented Generation`.

En este proyecto quiere decir:

1. buscar fragmentos relevantes en documentos
2. entregar esos fragmentos al modelo generativo
3. redactar una respuesta usando esa evidencia

No es un chatbot libre: responde apoyado en documentos.

## Corpus

Conjunto organizado de documentos que alimenta al sistema.

En AGROJ, el corpus esta compuesto por PDFs sobre agricultura, agroecologia, cultivos, territorio rural y saberes ancestrales.

## Embeddings

Representaciones numericas del texto.

Sirven para comparar significados. Por ejemplo, permiten detectar que una pregunta sobre "sembrar papa" esta relacionada con fragmentos que hablen de cultivo, semilla, suelo o manejo agricola.

Modelo usado:

```text
sentence-transformers/all-MiniLM-L6-v2
```

## LlamaIndex

Framework usado para construir el flujo RAG.

En el proyecto ayuda a:

- dividir documentos en fragmentos
- crear indices
- conectar embeddings
- recuperar informacion relevante

## Gemini

Modelo generativo principal.

Se usa para redactar respuestas naturales a partir de la pregunta y los fragmentos recuperados.

Modelo principal:

```text
gemini-2.5-flash
```

Modelo fallback:

```text
gemini-2.5-flash-lite
```

## spaCy

Libreria de procesamiento de lenguaje natural.

Se usa para enriquecer documentos con:

- entidades
- temas
- terminos clave

Si no hay un modelo de espanol disponible, el sistema usa reglas propias de dominio para no bloquear el flujo.

## NLTK

Libreria clasica de NLP.

No forma parte del runtime actual. Podria evaluarse en el futuro para stopwords, tokenizacion o limpieza adicional, pero hoy las necesidades estan cubiertas por spaCy, reglas propias y embeddings.

## Cloud Run

Servicio de Google Cloud que ejecuta contenedores web.

En AGROJ ejecuta:

- backend API
- frontend estatico servido con Nginx

## Cloud Run Jobs

Servicio para ejecutar tareas batch.

En AGROJ ejecuta el reindexado, que puede tardar bastante cuando hay muchos PDFs.

## Cloud Storage

Almacenamiento de objetos de Google Cloud.

En AGROJ guarda:

- PDFs originales
- indices generados
- manifiestos
- chunk cache

## Firestore

Base de datos NoSQL de Google Cloud.

En AGROJ guarda:

- metadatos de documentos
- estado de reindexado
- progreso
- estado runtime
- preguntas frecuentes

## Secret Manager

Servicio para guardar secretos.

En AGROJ protege:

- `GEMINI_API_KEY`
- `ADMIN_SESSION_SECRET`

## Reindexado

Proceso que reconstruye el indice consultable a partir de los PDFs.

Incluye:

- leer PDFs
- extraer texto
- dividir fragmentos
- calcular embeddings
- construir indice
- publicar artefactos
- actualizar Firestore

## No-op

Significa `no operation`.

Ocurre cuando se pide reindexar, pero el sistema detecta que los documentos no cambiaron. En ese caso evita reconstruir todo.

## Manifest

Archivo que resume que documentos forman parte del indice.

Sirve para saber:

- que PDFs fueron considerados
- si cambiaron archivos
- si el indice esta actualizado

## Chunk cache

Archivo con fragmentos procesados del corpus.

Sirve para:

- recuperar texto rapidamente
- responder con fallback lexical
- evitar releer PDFs en cada consulta

## Indice activo

Version del indice que usa actualmente la API.

En cloud se apunta mediante un alias o puntero estable, por ejemplo `current`.

## Materializar un indice

Preparar localmente un indice que vive en Cloud Storage para que el backend pueda usarlo.

Ejemplo:

```text
GCS -> cache local runtime -> RAGService
```

## Gestion documental

Area protegida del sistema para mantener el corpus.

Ruta:

```text
/gestion
```

Permite subir, revisar, eliminar documentos y lanzar reindexado.

## Cuentas autorizadas

Cuentas de Google permitidas para entrar a `/gestion`.

Se configuran con:

```text
ADMIN_EMAILS
```

## Estado `pending_index`

El documento existe, pero aun no entra al indice activo.

## Estado `indexed`

El documento ya forma parte del indice activo y puede aparecer en respuestas.

## Estado `failed`

El documento no pudo procesarse correctamente.

## Estado `deleted`

El documento fue eliminado del corpus operativo.

## Fallback

Respuesta alternativa cuando el flujo principal no esta disponible.

Ejemplo:

- Gemini tarda demasiado
- no hay evidencia suficiente
- el indice vectorial no esta listo

El fallback debe ser claro y honesto, no inventar informacion.
