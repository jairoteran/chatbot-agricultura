# Registro de evidencia

## Objetivo

Guardar evidencia util del proyecto para reutilizarla despues en:

- resultados
- implementacion
- pruebas
- anexos

## Que registrar

- capturas
- errores
- pruebas realizadas
- interfaces vistas o validadas
- avances tecnicos verificados

## Formato recomendado por entrada

### Fecha

- `YYYY-MM-DD`

### Tipo

- `captura`
- `error`
- `prueba`
- `interfaz`
- `avance`

### Contexto

- que se estaba intentando hacer

### Evidencia

- que se observo

## 2026-05-13 - Frontend listo para Hosting

- Contexto: el backend ya habia quedado plenamente operativo en Google Cloud, pero faltaba cerrar la publicacion del cliente web.
- Evidencia: se agregaron `firebase.json` y `.firebaserc` en la raiz para publicar `frontend/dist` en `Firebase Hosting`, con `rewrite` de `/api/**` hacia el servicio `Cloud Run` `tesis-producto-api` en `us-central1`.
- Evidencia: se agrego `scripts/deploy-frontend-hosting.ps1` para compilar el frontend y ejecutar `firebase deploy --only hosting`.
- Evidencia: `frontend/src/App.jsx` fue ajustado para mostrar `Cloud Run` cuando el backend reporta `deployment_mode=cloud-run`, evitando que la UI siga mostrando `Local` en produccion.

## 2026-05-13 - Bloqueo de permisos en Firebase Hosting y salida por Cloud Run

- Contexto: durante el primer intento real de publicar el frontend en Firebase Hosting, el proyecto no tenia ningun Hosting site creado.
- Evidencia: `npx firebase-tools hosting:sites:list --project project-838503ae-99e5-4041-837` devolvio una tabla vacia, confirmando ausencia total de sitios Hosting.
- Evidencia: al intentar crear el site `tesis-producto-1025954944056`, Firebase devolvio `403 PERMISSION_DENIED`, por lo que el bloqueo ya no era tecnico del frontend sino de permisos IAM sobre Hosting.
- Evidencia: como salida operativa se preparo despliegue alternativo del frontend en `Cloud Run` con `frontend/Dockerfile`, `frontend/nginx.conf`, `frontend/cloudbuild.frontend.yaml`, `scripts/build-frontend-image.ps1` y `scripts/deploy-frontend-cloudrun.ps1`.
- que pantalla o endpoint se reviso
- que resultado salio

## 2026-05-17 - Panel de gestion documental con autenticacion Google

- Contexto: se necesitaba dejar una vista protegida para operaciones internas sin cerrar el chat publico.
- Evidencia: se incorporo una ruta protegida `/gestion` dentro del frontend con tarjeta de acceso, paneles de resumen, documentos y monitoreo.
- Evidencia: el backend expone flujo de sesion de gestion documental, lista blanca de correos y endpoints protegidos para listar, subir y eliminar documentos.
- Evidencia: el archivo `backend/cloudrun.env.yaml` quedo preparado con `GOOGLE_AUTH_CLIENT_ID` y `ADMIN_EMAILS` para el despliegue cloud actual.

## 2026-05-17 - Error al intentar usar un boton Google completamente custom

- Contexto: se intento hacer que el acceso de gestion documental usara un boton visual 100 por ciento propio.
- Evidencia: el flujo termino mostrando mensajes equivalentes a `No se pudo completar el acceso` y `No fue posible abrir el acceso con Google en este momento`.
- Evidencia: la salida tecnica correcta fue mantener el click real sobre el renderizado de Google Identity Services y superponer una capa visual custom, en lugar de disparar un flujo manual inestable.

## 2026-05-17 - Reindexado automatico deshabilitado y paso a operacion manual

- Contexto: se decidio que la API web no reconstruya el indice por si sola cuando detecte cambios en los PDFs.
- Evidencia: `backend/app/rag_service.py` fue ajustado para dejar el indice como pendiente y exigir reindexado manual desde gestion documental.
- Evidencia: `frontend/src/App.jsx` incorporo un boton `Reindexar ahora` dentro del panel de documentos y refresco de estado despues de subir, borrar o reindexar.
- Evidencia: el panel ahora bloquea acciones concurrentes de subir, eliminar y reindexar para evitar estados intermedios del indice.

## 2026-05-17 - Riesgo detectado en cloud por depender de ALLOW_RUNTIME_REINDEX

- Contexto: tras quitar el rebuild automatico, el primer diseno seguia reutilizando la restriccion `ALLOW_RUNTIME_REINDEX` tambien para el reindex manual.
- Evidencia: eso dejaba una contradiccion en cloud: la UI ofrecia `Reindexar ahora`, pero el backend podia rechazarlo justo en el despliegue donde el reindex automatico ya estaba desactivado.
- Evidencia: el backend fue corregido para permitir rebuild forzado cuando el reindex se dispara manualmente, manteniendo deshabilitado solo el rebuild automatico en runtime.

## 2026-05-30 - Subida directa de PDFs pesados a Cloud Storage

- Contexto: el panel de gestion documental ya no podia depender de requests web tradicionales porque `Cloud Run` impone limites de tamano y varios documentos reales superaban 30 MB.
- Evidencia: se rediseño el flujo de carga para pedir una sesion de subida desde backend y transferir el archivo directamente desde el navegador a `Cloud Storage`, dejando la API solo para autorizar y registrar metadatos.
- Evidencia: durante la primera validacion aparecio un error `No 'Access-Control-Allow-Origin' header is present`, que obligo a configurar `CORS` en el bucket documental y a propagar correctamente el header `Origin` al crear la sesion resumable.

## 2026-05-30 - Reindexado manual real mediante Cloud Run Jobs

- Contexto: el objetivo era que el boton `Reindexar ahora` del panel de gestion documental fuera manual, funcional y coherente con la arquitectura cloud.
- Evidencia: el flujo se ajusto para que la API lance el job `tesis-producto-reindex` en `Cloud Run Jobs` y marque primero un estado `queued` visible desde el panel.
- Evidencia: aparecio el error `Permission 'run.jobs.run' denied`, lo que obligo a conceder `roles/run.jobsExecutor` a la service account de la API para poder disparar el job desde backend.
- Evidencia: el panel de gestion documental quedo mostrando progreso real del reindexado, primero por estado de cola y luego por avance operativo persistido en backend.

## 2026-05-30 - Limpieza de tono y estructura de respuestas del asistente

- Contexto: se detecto que las respuestas sonaban demasiado documentales o mecanicas, con frases como `Respuesta breve`, `Puntos clave` y listas artificiales de palabras relevantes.
- Evidencia: `backend/app/rag_service.py` fue ajustado para responder de forma mas directa, natural y segura, dejando las fuentes en un panel aparte en lugar de repetir dentro del texto `segun el documento` o frases similares.
- Evidencia: se eliminaron encabezados forzados en respuestas y resúmenes, y tambien se quito la inyeccion de keywords mecanicas que generaba salidas poco naturales como `luis, hacer, guerrero`.

## 2026-05-31 - Gestion documental sin roles rigidos

- Contexto: se recibio la recomendacion de evitar presentar el sistema como dependiente de roles rigidos o de un unico administrador.
- Evidencia: se ajusto el lenguaje visible del frontend para hablar de `gestion documental`, `corpus` y `cuentas autorizadas` en la ruta `/gestion`.
- Evidencia: el backend mantiene endpoints y nombres tecnicos `admin` por compatibilidad, pero los mensajes devueltos al usuario ahora hablan de gestion documental y autorizacion sobre el corpus.
- Evidencia: `docs/architecture.md` registra la decision de mantener control operativo con cuentas autorizadas sin convertirlo metodologicamente en una jerarquia de roles.

## 2026-05-31 - Enriquecimiento NLP del corpus con spaCy

- Contexto: se busco fortalecer la tesis incorporando un modelo de corpus mas claro y una capa NLP adicional sin agregar dependencias innecesarias.
- Evidencia: `backend/app/metadata_models.py` amplio `DocumentRecord` con estados documentales y metadatos como `topics`, `entities`, `key_terms` y `nlp_analyzer`.
- Evidencia: `backend/app/corpus_analyzer.py` incorpora analisis con `spaCy` cuando esta disponible y fallback de dominio para mantener compatibilidad local/cloud.
- Evidencia: durante el reindexado, `backend/app/rag_service.py` agrupa fragmentos por documento y sincroniza los metadatos enriquecidos en Firestore mediante `metadata_repository.sync_documents`.
- Evidencia: el panel de gestion documental muestra estado de cada documento y etiquetas principales cuando existen.
- Decision: `NLTK` no se incorpora en runtime por ahora porque no aporta una mejora clara frente a `spaCy`, reglas propias de limpieza y embeddings actuales.

## 2026-05-31 - Cloud respondia distinto por usar lexical-only

- Contexto: despues del despliegue, las respuestas en cloud no sonaban igual que en local.
- Evidencia: `/health` de Cloud Run mostro `embed_model: lexical-only`, `index_source: chunk-cache` y `allow_reindex: false`, indicando que la API cloud no estaba cargando el indice vectorial.
- Causa: `ALLOW_RUNTIME_REINDEX=false` estaba acoplado indirectamente a no preparar el backend de embeddings, por lo que cloud degradaba a recuperacion lexica.
- Correccion: se agrego `ENABLE_VECTOR_RETRIEVAL` para permitir retrieval vectorial en la API web sin habilitar reconstruccion de indices durante trafico normal.

## 2026-05-31 - Diagnostico de caida generativa en cloud

- Contexto: aun con retrieval vectorial activo, una respuesta cloud salio como fallback extractivo y no con el tono conversacional que si aparecia en localhost.
- Evidencia: se agregaron `last_generation_status` y `last_generation_error` al estado de `/health` para saber si Gemini respondio, devolvio vacio o fallo durante la consulta.
- Evidencia: se mejoro el fallback extractivo para limpiar encabezados OCR y redactar con una entrada mas natural si el LLM no devuelve texto.
- Motivo: si Gemini falla por secreto, cuota, timeout, safety o respuesta vacia, el sistema ya no debe devolver fragmentos crudos como respuesta final.

## 2026-05-31 - Alta demanda de Gemini y 504 en frontend Cloud Run

- Contexto: el frontend reporto `POST /api/chat 504 Gateway Timeout` mientras la API registraba `503 UNAVAILABLE` de Gemini por alta demanda del modelo.
- Evidencia: `/health` mostro `last_generation_error` con `This model is currently experiencing high demand` y latencia de respuesta de mas de 37 segundos.
- Correccion: se agrego `GEMINI_FALLBACK_MODEL` para intentar un segundo modelo Gemini cuando el principal devuelva `503 UNAVAILABLE`.
- Correccion: `frontend/nginx.conf` amplio `proxy_connect_timeout`, `proxy_send_timeout` y `proxy_read_timeout` a `120s` para evitar cortes prematuros del proxy del frontend en Cloud Run.

## 2026-05-31 - Objetivo de respuesta menor a 3 segundos

- Contexto: se definio que el chat debe priorizar tiempos de respuesta menores a 3 segundos.
- Evidencia: se agrego `LLM_TIMEOUT_SECONDS` con valor recomendado `2.2` para cortar llamadas lentas al proveedor generativo antes de que la API supere el objetivo de latencia.
- Decision: si Gemini no responde dentro de esa ventana, el sistema debe devolver un fallback limpio basado en recuperacion documental antes que bloquear la interfaz.
- Riesgo aceptado: una respuesta fallback puede ser menos natural que una respuesta generativa completa, pero evita `504 Gateway Timeout` y mantiene la experiencia operativa.

## 2026-05-30 - Simplificacion de la interfaz publica y experiencia movil

- Contexto: la interfaz publica seguia mostrando elementos secundarios que quitaban espacio al chat, especialmente en celulares.
- Evidencia: se ocultaron contadores internos de documentos, bloques secundarios como la biblioteca lateral y se limpiaron titulos feos del selector de resumen para mostrar nombres mas legibles.
- Evidencia: en movil se rediseño el sidebar como un drawer desplegable, dejando el chat como pantalla principal y moviendo al menu lateral las herramientas de resumen y preguntas frecuentes.
- Evidencia: en la primera iteracion el panel lateral quedo abierto permanentemente por un choque entre `motion` y `transform` en CSS; la correccion final cambio ese comportamiento a una apertura controlada por posicion lateral para que el drawer arranque realmente cerrado.

## 2026-06-02 - Saludo inicial mas neutro

- Contexto: el mensaje inicial del chat publico mencionaba que el asistente estaba listo para analizar documentos cargados, aunque la primera interaccion no siempre parte de una carga explicita del usuario.
- Evidencia: se cambio el saludo inicial en `frontend/src/App.jsx` por una frase mas general: `Hola. Estoy listo para ayudarte. Puede hacer preguntas, pedir resúmenes o comparar información cuando lo necesite.`
- Evidencia: se ejecuto `npm run build` en `frontend` y el texto anterior dejo de aparecer en el proyecto.
- Resultado: `correcto`
- Uso futuro: `interfaz`, `implementacion`, `pruebas`

### Resultado

- correcto
- incorrecto
- pendiente

### Uso futuro

- resultados
- implementacion
- pruebas
- anexos

## Entradas

### 2026-05-10

- Tipo: `avance`
- Contexto: integracion inicial de Firestore como backend real de metadatos y estado para el backend local.
- Evidencia: el backend respondio en `/health` con `status: ok`, `metadata_backend: firestore`, `process_state_backend: firestore`, `index_ready: true` y `runtime_last_reindex_status: success`.
- Resultado: `correcto`
- Uso futuro: `implementacion`, `pruebas`, `resultados`

### 2026-05-10

- Tipo: `captura`
- Contexto: validacion visual de Firestore tras la sincronizacion inicial de documentos.
- Evidencia: en Firestore aparecieron las colecciones `documents` y `runtime_state`. En `documents` se observaron campos como `file_name`, `relative_path`, `fingerprint`, `size`, `status` y `storage_path` con prefijo `local:`.
- Resultado: `correcto`
- Uso futuro: `resultados`, `anexos`, `implementacion`

### 2026-05-11

- Tipo: `captura`
- Contexto: validacion visual del registro de jobs de reindexado en Firestore.
- Evidencia: aparecio la coleccion `reindex_jobs` con un documento `job-99bf60f194434e20` que registro `status: success`, `trigger: api`, `source: local`, `started_at`, `finished_at` y `release_name: local`.
- Resultado: `correcto`
- Uso futuro: `pruebas`, `resultados`, `anexos`

### 2026-05-11

- Tipo: `error`
- Contexto: primer intento de usar Firestore desde el backend local.
- Evidencia: `/health` respondio con `403 Permission denied on resource project tesis-producto-dev` y razon `CONSUMER_INVALID` hasta corregir el uso del Project ID real y el quota project de ADC.
- Resultado: `resuelto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-11

- Tipo: `avance`
- Contexto: migracion del almacenamiento del indice a Cloud Storage con reindexado exitoso.
- Evidencia: el backend reporto `index_storage_backend: gcs`, `runtime_active_index_name: current` y `runtime_active_index_source: gcs`. En el bucket `tesis-producto-dev-indexes` aparecieron `active-index.json`, releases del indice y archivos persistidos del indice.
- Resultado: `correcto`
- Uso futuro: `resultados`, `implementacion`, `pruebas`, `anexos`

### 2026-05-11

- Tipo: `avance`
- Contexto: mejora de experiencia operativa del reindexado local.
- Evidencia: el script `scripts/reindex-local.ps1` fue actualizado para ejecutar `POST /reindex` en segundo plano y mostrar porcentaje, etapa y detalle obtenidos desde `/health` durante el proceso.
- Resultado: `correcto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-11

- Tipo: `avance`
- Contexto: ajuste del estado runtime durante el reindexado y pequena optimizacion post-publicacion del indice.
- Evidencia: el backend ahora propaga `current_reindex_job_id` al actualizar el indice activo y evita rematerializar el indice desde GCS inmediatamente despues de publicar, reutilizando el directorio runtime del repositorio.
- Resultado: `correcto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-11

- Tipo: `avance`
- Contexto: optimizacion del endpoint `/reindex` para evitar reconstrucciones completas innecesarias.
- Evidencia: antes de lanzar un rebuild completo, el backend ahora compara el manifiesto actual con el almacenado y, si no hubo cambios en los PDFs y el indice materializado sigue disponible, responde que el indice ya estaba actualizado sin rehacer embeddings ni persistencia.
- Resultado: `correcto`
- Uso futuro: `implementacion`, `pruebas`, `resultados`

### 2026-05-11

- Tipo: `error`
- Contexto: consulta a `/health` inmediatamente despues de un `reindex` con `INDEX_STORAGE_BACKEND=gcs`.
- Evidencia: el backend lanzo `json.decoder.JSONDecodeError: Unterminated string...` al leer `chunk_cache.json` del cache runtime mientras el repositorio de indices aun lo estaba descargando o reemplazando.
- Resultado: `resuelto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-11

- Tipo: `avance`
- Contexto: endurecimiento del repositorio de indices en GCS ante concurrencia entre `reindex` y `health`.
- Evidencia: la sincronizacion del indice runtime ahora descarga a un directorio temporal y reemplaza los archivos del cache local de forma controlada, evitando lecturas de JSON incompleto durante las consultas de estado.
- Resultado: `correcto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-11

- Tipo: `avance`
- Contexto: optimizacion del entrypoint batch de reindexado para casos sin cambios.
- Evidencia: `python -m app.reindex_job` fue ajustado para iniciar `RAGService` sin auto-inicializacion ni embeddings eager, de modo que el job solo prepare embeddings si realmente necesita reconstruir el indice.
- Resultado: `correcto`
- Uso futuro: `implementacion`, `pruebas`, `resultados`

### 2026-05-11

- Tipo: `prueba`
- Contexto: medicion del tiempo del entrypoint batch sin cambios en los PDFs.
- Evidencia: `Measure-Command { python -m app.reindex_job }` reporto aproximadamente `29.78` segundos, mejorando frente a la ejecucion anterior de mas de un minuto en el camino no-op.
- Resultado: `correcto`
- Uso futuro: `resultados`, `pruebas`, `implementacion`

### 2026-05-11

- Tipo: `error`
- Contexto: impresion del resultado JSON del job batch en consola Windows.
- Evidencia: `python -m app.reindex_job` fallo con `UnicodeEncodeError` al intentar imprimir caracteres no soportados por `cp1252`.
- Resultado: `resuelto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-11

- Tipo: `prueba`
- Contexto: segunda medicion del job batch sin cambios tras corregir la salida UTF-8.
- Evidencia: `Measure-Command { python -m app.reindex_job }` termino correctamente y reporto aproximadamente `29.76` segundos sin `UnicodeEncodeError`.
- Resultado: `correcto`
- Uso futuro: `pruebas`, `resultados`, `implementacion`

### 2026-05-11

- Tipo: `error`
- Contexto: primer intento de crear el Cloud Run Job mediante el script auxiliar del repositorio.
- Evidencia: `scripts/deploy-reindex-job.ps1` invoco `gcloud run jobs create` con `--args` separado del valor `-m,app.reindex_job`, lo que produjo `argument --args: expected one argument`. Ademas, el script imprimia `Cloud Run Job listo` incluso cuando `gcloud` fallaba.
- Resultado: `resuelto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-11

- Tipo: `avance`
- Contexto: endurecimiento del script de despliegue del Cloud Run Job.
- Evidencia: `scripts/deploy-reindex-job.ps1` ahora pasa `--args=-m,app.reindex_job`, detecta correctamente si el job ya existe y corta la ejecucion si `gcloud` devuelve error, evitando falsos positivos en el flujo de despliegue.
- Resultado: `correcto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-11

- Tipo: `error`
- Contexto: segundo intento de desplegar el Cloud Run Job desde PowerShell.
- Evidencia: el chequeo previo con `gcloud run jobs describe` provocaba `Cannot find job [tesis-producto-reindex]` como error nativo en PowerShell cuando el job aun no existia, interrumpiendo el flujo antes de crearlo.
- Resultado: `resuelto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-11

- Tipo: `error`
- Contexto: intento de crear el Cloud Run Job usando `backend/cloudrun.env.yaml`.
- Evidencia: `gcloud run jobs create` rechazo `--env-vars-file` porque `ALLOW_RUNTIME_REINDEX` estaba serializado como booleano YAML (`true`) en lugar de string, y Cloud Run exige valores de variables como cadenas.
- Resultado: `resuelto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-12

- Tipo: `avance`
- Contexto: preparacion del siguiente bloque para desplegar la API principal en Cloud Run.
- Evidencia: se agrego `scripts/deploy-backend-api.ps1` para desplegar o actualizar el servicio `tesis-producto-api`, reutilizando la misma imagen del backend y permitiendo inyectar `GEMINI_API_KEY` desde Secret Manager mediante `-GeminiApiSecret`.
- Resultado: `correcto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-12

- Tipo: `avance`
- Contexto: preparacion del manejo correcto de secretos para el despliegue cloud de la API.
- Evidencia: se agrego `scripts/set-gemini-secret.ps1` para crear o actualizar `GEMINI_API_KEY` en Secret Manager sin dejar la clave dentro de `cloudrun.env.yaml`.
- Resultado: `correcto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-12

- Tipo: `error`
- Contexto: primera validacion del endpoint `/health` en la API desplegada en Cloud Run.
- Evidencia: el servicio quedaba indefinidamente en `status: checking` con `init_progress: 2` porque la inicializacion de `RAGService` se ejecutaba en un hilo daemon en segundo plano. En Cloud Run eso puede quedarse sin progreso estable por el modelo de CPU del contenedor entre solicitudes.
- Resultado: `resuelto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-12

- Tipo: `avance`
- Contexto: ajuste del arranque de la API para el entorno Cloud Run.
- Evidencia: `backend/app/main.py` fue modificado para que, cuando `APP_DEPLOYMENT_TARGET=cloud-run`, la inicializacion del servicio se ejecute de forma sincronica y controlada bajo `init_lock`, evitando que `/health` quede eternamente en estado de arranque.
- Resultado: `correcto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-12

- Tipo: `error`
- Contexto: redeploy posterior de la API en Cloud Run tras mover la inicializacion a modo sincronico.
- Evidencia: la revision no llego a escuchar `PORT=8080` dentro del tiempo esperado porque el contenedor intentaba inicializar completamente `RAGService` durante el `startup` antes de que `uvicorn` quedara disponible.
- Resultado: `resuelto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-12

- Tipo: `avance`
- Contexto: ajuste final del arranque para compatibilidad con Cloud Run.
- Evidencia: el hook `startup_event` ahora omite la inicializacion pesada cuando el despliegue es `cloud-run`, permitiendo que el contenedor arranque y escuche el puerto primero; la inicializacion controlada queda para la primera solicitud.
- Resultado: `correcto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-12

- Tipo: `error`
- Contexto: validacion del endpoint `/health` tras el redeploy de la API principal en Cloud Run.
- Evidencia: la revision `tesis-producto-api-00004-r9t` devolvia `503` porque la instancia superaba el limite de memoria de `512Mi` durante la inicializacion real del servicio. Los logs de Cloud Run registraron `Memory limit of 512 MiB exceeded`.
- Resultado: `resuelto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-12

- Tipo: `avance`
- Contexto: ajuste de recursos del despliegue de la API en Cloud Run.
- Evidencia: `scripts/deploy-backend-api.ps1` fue actualizado para desplegar la API con `1Gi` de memoria por defecto, suficiente para la carga inicial observada en esta fase.
- Resultado: `correcto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-12

- Tipo: `avance`
- Contexto: separacion del perfil operativo entre API cloud y job batch.
- Evidencia: `scripts/deploy-backend-api.ps1` ahora genera un archivo temporal de variables para forzar `ALLOW_RUNTIME_REINDEX=false` en la API de Cloud Run, evitando que el servicio web intente comportarse como un proceso de reindexado en vivo.
- Resultado: `correcto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-12

- Tipo: `error`
- Contexto: validacion del `/health` de la API tras separar el perfil de la API del job batch.
- Evidencia: la inicializacion sincronica del servicio podia completarse durante la misma solicitud, pero `backend/app/main.py` seguia devolviendo `status: checking` porque no revaluaba `rag_service` despues de `ensure_service_initializing`.
- Resultado: `resuelto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-12

- Tipo: `avance`
- Contexto: ajuste de las rutas para reflejar mejor el estado real de inicializacion en Cloud Run.
- Evidencia: `/health`, `/reindex`, `/chat` y `/summarize-document` ahora reintentan usar `rag_service` inmediatamente despues de `ensure_service_initializing`, evitando respuestas de espera innecesarias cuando la inicializacion ya termino dentro de la misma solicitud.
- Resultado: `correcto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-12

- Tipo: `prueba`
- Contexto: validacion final de la API principal desplegada en Cloud Run despues de los ajustes de memoria, arranque e inicializacion.
- Evidencia: `/health` respondio con `status: ok`, `deployment_mode: cloud-run`, `document_storage_backend: local`, `index_storage_backend: gcs`, `metadata_backend: firestore`, `process_state_backend: firestore`, `indexed_file_count: 36` y `runtime_last_reindex_status: success`.
- Resultado: `correcto`
- Uso futuro: `resultados`, `pruebas`, `implementacion`, `anexos`

### 2026-05-13

- Tipo: `avance`
- Contexto: preparacion del bloque para eliminar la dependencia de `backend/data/` como backend documental obligatorio.
- Evidencia: se implemento `backend/app/document_repository.py` con soporte `local|gcs`, de modo que el backend ya puede construir manifiestos desde metadatos de `Cloud Storage` y descargar los PDFs al cache local solo cuando realmente necesita reindexar.
- Resultado: `correcto`
- Uso futuro: `implementacion`, `pruebas`, `resultados`

### 2026-05-13

- Tipo: `avance`
- Contexto: preparacion operativa de la migracion de documentos al bucket cloud.
- Evidencia: se agrego `scripts/sync-documents-to-gcs.ps1` para sincronizar `backend/data/` al bucket `tesis-producto-dev-documents`, y los scripts `deploy-backend-api.ps1` y `deploy-reindex-job.ps1` ahora aceptan `-DocumentStorageBackend gcs` sin editar manualmente `backend/cloudrun.env.yaml`.
- Resultado: `correcto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-13

- Tipo: `prueba`
- Contexto: validacion del paso final de migracion de documentos al backend cloud.
- Evidencia: los PDFs fueron sincronizados a `gs://tesis-producto-dev-documents/documents`, el job `tesis-producto-reindex-khb9g` termino correctamente leyendo `DOCUMENT_STORAGE_BACKEND=gcs`, y la API devolvio `/health` con `document_storage_backend: gcs`, `index_storage_backend: gcs` y `runtime_last_reindex_status: success`.
- Resultado: `correcto`
- Uso futuro: `resultados`, `pruebas`, `implementacion`, `anexos`

### 2026-05-13

- Tipo: `avance`
- Contexto: limpieza del contenedor para completar el desacoplamiento cloud.
- Evidencia: `backend/Dockerfile` dejo de copiar `backend/data/` a la imagen y `backend/cloudrun.env.yaml` paso a usar `DOCUMENT_STORAGE_BACKEND=gcs` por defecto para Cloud Run.
- Resultado: `correcto`
- Uso futuro: `implementacion`, `resultados`, `anexos`

### 2026-05-13

- Tipo: `avance`
- Contexto: endurecimiento del script de sincronizacion documental para evitar subir archivos no requeridos.
- Evidencia: `scripts/sync-documents-to-gcs.ps1` ahora arma un staging temporal con solo archivos `*.pdf` antes del `gcloud storage rsync`, y agrega la opcion `-DeleteUnmatchedDestinationObjects` para limpiar blobs sobrantes del bucket si se desea.
- Resultado: `correcto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-13

- Tipo: `error`
- Contexto: primer reindexado cloud despues de quitar `backend/data/` de la imagen del contenedor.
- Evidencia: la ejecucion `tesis-producto-reindex-nf6wl` fallo en Cloud Run Jobs con `The configured memory limit was reached` mientras seguia desplegada con `512Mi`.
- Resultado: `resuelto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-13

- Tipo: `avance`
- Contexto: ajuste de recursos del Cloud Run Job para el reindexado cloud definitivo.
- Evidencia: `scripts/deploy-reindex-job.ps1` fue actualizado para desplegar el job con `2Gi` de memoria por defecto, valor mas acorde al consumo del rebuild de embeddings e indice leyendo documentos desde `GCS`.
- Resultado: `correcto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-13

- Tipo: `error`
- Contexto: segundo intento de reindexado cloud tras aumentar memoria del job.
- Evidencia: la ejecucion `tesis-producto-reindex-qb2mx` ya no fallo por memoria, pero termino con `The configured timeout was reached` manteniendo `1 vCPU` y `Task Timeout: 10m`.
- Resultado: `resuelto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-13

- Tipo: `avance`
- Contexto: segundo ajuste de recursos del Cloud Run Job para permitir el rebuild completo desde `GCS`.
- Evidencia: `scripts/deploy-reindex-job.ps1` fue actualizado para desplegar el job con `2Gi`, `2 vCPU` y `60m` de timeout por defecto.
- Resultado: `correcto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-05-13

- Tipo: `avance`
- Contexto: correccion de una inconsistencia final en el estado runtime expuesto por `/health`.
- Evidencia: cuando el indice activo quedaba listo tras un reindexado exitoso, pero Firestore aun arrastraba un `last_reindex_status: failed` viejo, el backend ahora reconcilia automaticamente el runtime a `success` si el indice materializado esta sano y no esta marcado como stale.
- Resultado: `correcto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-06-06

- Tipo: `avance`
- Contexto: se pidio filtrar mejor los documentos al subirlos y evitar mensajes frios o demasiado tecnicos en `/gestion`.
- Evidencia: `backend/app/corpus_analyzer.py` ahora inspecciona el PDF al subirlo, intenta extraer texto, calcula relevancia tematica y guarda `topics`, `entities`, `key_terms`, `nlp_analyzer` y `nlp_model` desde el ingreso del archivo.
- Evidencia: si el PDF no es legible o no parece suficientemente relacionado con agricultura o saberes ancestrales, la subida se rechaza con un mensaje mas amigable.
- Evidencia: `frontend/src/App.jsx` reformula el error de subida para que el usuario vea explicaciones mas naturales dentro del panel `/gestion`.
- Evidencia: `backend/app/rag_service.py` dejo de mencionar `corpus` en el tono visible de las respuestas fallback del chat.
- Resultado: `correcto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`

### 2026-06-06

- Tipo: `avance`
- Contexto: se pidio que las preguntas frecuentes dejaran de ser fijas y pasaran a depender de lo que mas pregunta la gente.
- Evidencia: `backend/app/metadata_repository.py` ahora registra preguntas normalizadas en el estado runtime y conserva un ranking persistente de consultas repetidas.
- Evidencia: `backend/app/rag_service.py` expone esas preguntas frecuentes en `/health`, lo que permite reutilizarlas sin crear un endpoint aparte.
- Evidencia: `frontend/src/App.jsx` reemplazo la lista hardcodeada por las preguntas frecuentes reales y actualiza la sugerencia visible despues de cada nueva consulta.
- Resultado: `correcto`
- Uso futuro: `implementacion`, `pruebas`, `anexos`
