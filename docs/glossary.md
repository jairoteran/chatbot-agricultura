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
