# Glosario

## no-op

Significa `no operation`.

En este proyecto, un `no-op` ocurre cuando se solicita un reindexado pero el sistema detecta que los PDFs no cambiaron y, por tanto, no necesita reconstruir el indice completo.

Resultado practico:

- no recalcula embeddings
- no rehace el indice vectorial
- responde rapido indicando que el indice ya estaba actualizado

## job batch

Es una ejecucion de una tarea en segundo plano, fuera del flujo normal de peticiones web.

En este proyecto, el reindexado como `job batch` significa:

- correr el proceso como tarea independiente
- no depender de `uvicorn` ni de un endpoint HTTP para ejecutar toda la logica
- usar un entrypoint como `python -m app.reindex_job`

Ventajas:

- mejor para procesos largos
- mas adecuado para Cloud Run Jobs
- separa trafico de usuarios de tareas pesadas

## entrypoint batch

Es el comando o modulo que inicia un proceso batch.

En este proyecto:

- `python -m app.reindex_job`

Ese comando permite ejecutar el reindexado como proceso independiente del servidor web.

## runtime state

Es el estado operativo actual del sistema.

En este proyecto, incluye datos como:

- indice activo
- origen del indice activo
- ultimo estado del reindexado
- ultimo `job_id` ejecutado

Se guarda en Firestore dentro de `runtime_state`.

## manifest

Es un resumen estructurado de los PDFs que componen el indice.

Incluye por archivo:

- nombre
- ruta relativa
- tamano
- fingerprint

Sirve para detectar si hubo cambios reales en los documentos antes de decidir si hay que reconstruir el indice.

## chunk cache

Es una representacion serializada de los fragmentos de texto usados por el sistema.

Cada fragmento guarda:

- archivo origen
- pagina
- texto
- tokens

Sirve para:

- responder consultas sin depender siempre del indice vectorial completo
- acelerar algunos caminos de lectura

## materializar un indice

Significa descargar o preparar localmente los archivos necesarios de un indice para poder usarlos.

En este proyecto, cuando el indice vive en GCS:

- se descarga a un cache local
- luego el backend lo usa desde ese directorio runtime

## corpus

Es el conjunto organizado de documentos que alimenta al sistema.

En este proyecto, el corpus esta compuesto por PDFs sobre agricultura, agroecologia y saberes ancestrales.

Su valor practico es que:

- define la base real de conocimiento del asistente
- permite justificar academicamente de donde sale la informacion
- separa el sistema de un chatbot generativo libre

## RAG

Significa `Retrieval-Augmented Generation`.

En este proyecto quiere decir que el sistema:

1. recupera fragmentos relevantes del corpus
2. envia ese contexto al modelo generativo
3. redacta una respuesta usando la informacion recuperada

## embeddings

Son representaciones numericas del texto que permiten comparar similitud semantica.

En este proyecto:

- se usan para indexar documentos
- ayudan a recuperar los fragmentos mas relacionados con una pregunta
- el modelo principal de embeddings es `sentence-transformers/all-MiniLM-L6-v2`

## Gemini

Es el modelo generativo principal del proyecto.

En este caso se usa `Gemini 2.5 Flash` para:

- interpretar preguntas
- redactar respuestas
- generar resumenes a partir del contexto recuperado

## Hugging Face

Es el ecosistema usado indirectamente para la capa de embeddings.

En este proyecto aparece mediante:

- `sentence-transformers`
- `llama-index-embeddings-huggingface`

Su papel actual no es el chatbot final, sino la recuperacion semantica del corpus.

## spaCy

Es una libreria de NLP orientada a produccion.

Todavia no esta integrada en el proyecto, pero se considera una mejora futura util para:

- extraer entidades
- limpiar texto
- detectar conceptos o temas con mas precision

## NLTK

Es una libreria clasica de procesamiento de lenguaje natural.

Actualmente no forma parte del sistema, pero podria servir en el futuro para:

- stopwords personalizadas
- tokenizacion adicional
- limpieza o normalizacion basica del texto
