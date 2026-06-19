# Estado del proyecto

## Resumen

Este documento registra que ya esta hecho, que se decidio y que sigue. Debe actualizarse despues de cada bloque de trabajo importante.

## Hecho

- Existe un frontend funcional en React + Vite
- Existe un backend funcional en FastAPI
- Existe un flujo local de RAG con PDFs e indice persistido localmente
- Existe un endpoint de reindexado local
- Se definio la nueva arquitectura objetivo en Google Cloud
- Se reorganizo la documentacion para que el repo sea la referencia central de trabajo
- Se creo un modulo central de configuracion del backend para separar modo local y modo cloud
- Se agrego `backend/.env.example` con variables base para la futura migracion
- `/health` ahora puede exponer el backend de documentos, indices y metadatos configurado
- Se definio en codigo un contrato inicial para manifiestos, chunk cache y layout cloud de indices
- Se implemento un repositorio de indices `local|gcs` para desacoplar el servicio RAG del filesystem fijo
- Se implemento un repositorio de metadatos `none|firestore` para documentos, jobs y estado runtime
- Se configuro el entorno local para probar Firestore real como backend de metadatos y estado
- Se creo un registro formal de evidencia para capturas, errores, pruebas, interfaces y avances
- Se valido la publicacion del indice en Cloud Storage usando `INDEX_STORAGE_BACKEND=gcs`
- Se mejoro el script de reindexado local para mostrar progreso porcentual durante la ejecucion
- Se ajusto el backend para propagar mejor el `reindex_job_id` al estado runtime y reducir una rematerializacion innecesaria desde GCS
- Se optimizo `/reindex` para evitar reconstrucciones completas cuando no hubo cambios en los PDFs
- Se creo un entrypoint batch del backend para reindexado independiente de FastAPI
- Se optimizo el entrypoint batch para evitar inicializacion pesada cuando el reindex no requiere rebuild
- Se preparo un contenedor reutilizable para la API y para Cloud Run Jobs
- Se agregaron scripts base para build de imagen y despliegue del reindexado como Cloud Run Job
- Se publico la primera imagen del backend en Artifact Registry
- Se corrigio el script de despliegue del Cloud Run Job para evitar errores con `--args` y falsos positivos de exito
- Se creo y ejecuto correctamente el primer `Cloud Run Job` real de reindexado contra Firestore y GCS
- Se preparo un script auxiliar para desplegar la API principal en Cloud Run, con soporte previsto para Secret Manager
- Se preparo un script auxiliar para crear o actualizar `GEMINI_API_KEY` en Secret Manager
- La API principal ya quedo desplegada y saludable en Cloud Run usando `Secret Manager`, `GCS` para indices y `Firestore` para estado y metadatos
- Se implemento un repositorio de documentos `local|gcs` para desacoplar la lectura de PDFs de `backend/data/`
- Se agrego un script para sincronizar los PDFs locales al bucket de documentos y se habilito el override `-DocumentStorageBackend` en los scripts de despliegue cloud
- Se migro el backend cloud a `DOCUMENT_STORAGE_BACKEND=gcs` y la imagen del contenedor ya no empaqueta `backend/data/`
- Se agrego reconciliacion automatica del estado runtime para que `/health` no siga mostrando un `failed` viejo cuando el indice activo ya esta sano
- Se preparo el despliegue del frontend en `Firebase Hosting` con `rewrite` de `/api/**` hacia `Cloud Run` y script dedicado de publicacion
- Se preparo una ruta alternativa de despliegue del frontend en `Cloud Run` para evitar el bloqueo actual de permisos en Firebase Hosting
- Se incorporo un panel de gestion documental protegido con Google Sign-In para gestionar acceso interno
- Se implemento carga manual, listado y eliminacion de PDFs desde el panel de gestion documental
- Se conecto el panel de gestion documental con sesiones validadas por backend y lista blanca de correos autorizados
- Se reemplazo el boton visual nativo de Google por una capa visual custom manteniendo el flujo real de autenticacion por debajo
- Se elimino el reindexado automatico en runtime y el flujo quedo completamente manual desde el panel de gestion documental
- Se agrego una accion manual `Reindexar ahora` en el panel de documentos y se bloquearon acciones concurrentes de subir, borrar y reindexar
- Se dejo configurado `backend/cloudrun.env.yaml` con `GOOGLE_AUTH_CLIENT_ID` y `ADMIN_EMAILS` para el despliegue cloud actual
- Se implemento subida de PDFs pesados directa a `Cloud Storage` desde el navegador para evitar el limite de `Cloud Run` en requests grandes
- Se ajusto el flujo manual de reindexado en cloud para que el panel de gestion documental dispare `Cloud Run Jobs` en lugar de reconstruir el indice dentro de la API web
- Se agrego progreso operativo del reindexado en el panel de gestion documental, con estado persistido en backend y seguimiento visible desde la UI
- Se mejoro la redaccion de respuestas y resúmenes para que suenen mas directos y naturales, sin encabezados fijos como `Respuesta breve`, `Puntos clave` o `Conclusion`
- Se corrigio la extraccion mecanica de keywords que generaba frases poco naturales como listas de nombres sueltos dentro de la respuesta
- Se simplifico la interfaz publica ocultando contadores internos de documentos y bloques secundarios no necesarios para el usuario final
- Se limpio el selector de documentos del resumen para mostrar titulos mas legibles sin cambiar el nombre real del archivo usado por el backend
- Se rediseño la experiencia movil del chat publico con menu lateral desplegable, dejando el chat como vista principal y moviendo herramientas secundarias al drawer movil
- Se ajusto el lenguaje visible del panel `/gestion` para presentarlo como `gestion documental` basada en cuentas autorizadas, evitando describirlo como un rol unico de administrador
- Se agrego un modelo documental mas claro para el corpus con estados como `pending_index` e `indexed`, mas metadatos NLP (`topics`, `entities`, `key_terms`, `nlp_analyzer`)
- Se integro una capa de analisis de corpus con `spaCy` y fallback de dominio para enriquecer documentos durante el reindexado sin depender obligatoriamente de un modelo externo instalado
- Se incorporo un filtro automatico en la subida de PDFs para aceptar solo documentos con suficiente relacion tematica, guardar metadatos NLP desde el ingreso y devolver mensajes de rechazo mas amigables en `/gestion`
- Se decidio no integrar `NLTK` en runtime por ahora, porque la limpieza/tokenizacion queda cubierta por `spaCy`, reglas propias y embeddings
- Se separo `ENABLE_VECTOR_RETRIEVAL` de `ALLOW_RUNTIME_REINDEX` para que cloud pueda usar el indice vectorial publicado sin permitir rebuilds pesados dentro de la API web
- Se agrego trazabilidad de generacion (`last_generation_status`, `last_generation_error`) para diagnosticar cuando cloud cae al fallback extractivo en lugar de responder con Gemini
- Se suavizo el fallback extractivo para evitar respuestas con encabezados OCR o bloques crudos si Gemini no devuelve texto
- Se agrego `GEMINI_FALLBACK_MODEL` para intentar un modelo Gemini alternativo cuando `gemini-2.5-flash` responde `503 UNAVAILABLE` por alta demanda
- Se amplio el timeout del proxy Nginx del frontend en Cloud Run para evitar `504 Gateway Timeout` durante respuestas generativas lentas
- Se agrego `LLM_TIMEOUT_SECONDS=2.2` para cortar la espera de Gemini y mantener la API orientada a respuestas menores a 3 segundos, usando fallback limpio si el modelo no responde a tiempo
- Se ajusto el mensaje inicial del chat publico para que no asuma ni mencione una carga previa de documentos
- Se optimizo el arranque de la API en Cloud Run para cargar rapidamente el indice publicado desde `chunk_cache` sin bloquear la pagina esperando el backend de embeddings
- Se eliminaron menciones al `corpus` dentro del tono visible de las respuestas del chat y se reforzo un estilo mas conversacional, directo y natural
- Se volvieron dinamicas las `Preguntas frecuentes`, tomando como base las consultas reales mas repetidas y persistiendo ese ranking en el estado runtime del backend
- Se movio tambien el arranque de cloud a inicializacion en segundo plano para que `/health` responda antes y la UI no quede tanto tiempo bloqueada en `Preparando sistema`
- Se agrego un timeout configurable para la carga de embeddings (`EMBEDDING_INIT_TIMEOUT_SECONDS`), permitiendo que cloud arranque en modo rapido si Hugging Face tarda demasiado en inicializarse
- Se estabilizo el `document_id` de metadatos por `relative_path` para evitar registros duplicados en Firestore y corregir casos donde un PDF seguia apareciendo como `pending_index` despues del reindexado cloud

## En progreso

- Transicion desde arquitectura local versionada en Git hacia almacenamiento administrado en Google Cloud
- Publicacion y validacion final del frontend y backend actualizados en cloud
- Ajuste fino de experiencia movil y tono conversacional del asistente sobre pruebas reales en localhost y cloud
- Evolucion metodologica del corpus hacia gestion documental sin roles rigidos y enriquecimiento NLP con `spaCy`
- Revision de textos visibles para que el chat publico suene mas general cuando el usuario aun no ha dado contexto
- Validacion del arranque rapido en Cloud Run para reducir el tiempo visible en `Preparando sistema`

## Pendiente inmediato

- Construir y desplegar backend y frontend con la version actual del panel de gestion documental
- Ejecutar validacion extremo a extremo del flujo de gestion documental: login, subida, reindex manual, consulta y borrado
- Verificar el comportamiento del job de reindexado cloud despues del redeploy
- Validar el nuevo drawer movil en dispositivos reales y ajustar breakpoints si algun telefono o tablet pequena requiere refinamiento

## Pendiente por fases

### Fase 1

- Documentar la estructura exacta de recursos cloud
- Preparar configuracion base del backend para usar variables orientadas a cloud
- Disenar flujo de lectura y escritura de documentos e indices fuera de `backend/data/` y `backend/storage/`

### Fase 2

- Implementar integracion con Cloud Storage
- Implementar integracion con Firestore
- Implementar manejo de secretos para despliegue
- Preparar contenedor del backend para Cloud Run

### Fase 3

- Implementar job de reindexado para Cloud Run Jobs
- Conectar reindexado con metadatos y estado
- Ajustar frontend a la nueva API de estado

### Fase 4

- Validar frontend publicado en cloud
- Ejecutar prueba extremo a extremo contra la arquitectura cloud completa
- Consolidar instrucciones finales de despliegue y validacion

## Riesgos abiertos

- Si se despliega backend sin secretos o variables de acceso correctas, el panel `/gestion` quedara inaccesible aunque el resto de la API siga viva
- El flujo real del panel de gestion documental todavia requiere validacion final en cloud con login Google y subida real de PDFs
- Pueden quedar blobs antiguos no PDF en el bucket de documentos si se usaron sincronizaciones anteriores sin filtrado
- Falta definir una estrategia limpia de versionado del indice publicado
- La validacion completa del servicio RAG depende de disponibilidad del modelo de embeddings durante arranque
- Si `ENABLE_VECTOR_RETRIEVAL` queda apagado en cloud, la API responde con `lexical-only` y puede diferir notablemente de localhost
- Si `last_generation_status` aparece como `failed` o `empty`, revisar secreto/cuota/modelo de Gemini antes de evaluar la calidad del RAG
- El objetivo sub-3s exige aceptar un compromiso: si Gemini esta lento o saturado, el backend debe priorizar disponibilidad y devolver fallback antes que esperar una respuesta generativa larga

## Convenciones de seguimiento

- Si terminamos una tarea importante, marcarla en este archivo
- Si una decision cambia la arquitectura, actualizar tambien `architecture.md`
- Si algo deja de aplicar, eliminarlo en lugar de dejarlo obsoleto

## Proximo bloque recomendado

Disenar la estructura exacta de configuracion cloud:

- nombres de buckets
- colecciones Firestore
- variables de entorno
- flujo de publicacion del indice

## Nota del ultimo bloque

Se preparo la capa inicial de `settings` en el backend para que la migracion a Google Cloud no siga mezclando infraestructura con logica RAG. La validacion del servicio completo quedo parcialmente bloqueada por conectividad al descargar o resolver el modelo de embeddings.

En este bloque se agrego un `index_repository` para que el backend pueda trabajar con un indice local o con un indice materializado desde GCS. La escritura de releases y del puntero activo ya tiene una base en codigo, pero falta conectar metadatos y flujo de jobs.

En el bloque actual se agrego `metadata_repository` y el flujo de reindexado ya puede registrar jobs y estado runtime mediante un backend `noop` o `firestore`. Aun falta probar la integracion real contra servicios de Google Cloud.

En el siguiente bloque se activo `METADATA_BACKEND=firestore` y `PROCESS_STATE_BACKEND=firestore` en el entorno local para probar la primera integracion real con Firestore antes de mover indices y documentos a servicios cloud.

Se verifico en Firestore la escritura real de `documents`, `runtime_state` y `reindex_jobs`, y esa evidencia ya quedo registrada para reutilizarla despues en resultados, implementacion, pruebas y anexos.

Tambien se verifico la publicacion real del indice en el bucket `tesis-producto-dev-indexes`, y el flujo local de reindexado ahora muestra progreso usando la informacion de `/health` para reducir la incertidumbre durante procesos largos.

En el bloque mas reciente la API principal quedo funcionando en Cloud Run con `status: ok`, `deployment_mode: cloud-run`, `index_storage_backend: gcs`, `metadata_backend: firestore` y `process_state_backend: firestore`. El siguiente bloque ya se centra especificamente en sacar los PDFs de `backend/data/` y moverlos a `Cloud Storage` como backend documental real.

En el bloque actual se completo el panel de gestion documental protegido bajo `/gestion`, con autenticacion por Google, sesiones validadas por backend, carga y borrado manual de documentos, y reindexado manual disparado desde la UI. Tambien se decidio quitar el reindexado automatico en runtime para que el backend web no reconstruya el indice por si solo cuando detecta cambios documentales.

En los bloques posteriores se corrigio el flujo cloud para soportar PDFs grandes mediante subida directa del navegador a `Cloud Storage`, con politica `CORS` del bucket y registro posterior de metadatos. El panel de gestion documental quedo conectado a `Cloud Run Jobs` para ejecutar el reindexado real en cloud y mostrar progreso operativo al usuario.

En el bloque mas reciente se ajusto la experiencia del chat publico: se simplificaron elementos laterales visibles, se mejoro el tono del asistente para responder de forma mas directa y confiable, se limpiaron titulos documentales mostrados al usuario y se incorporo un menu lateral desplegable para pantallas moviles, dejando el chat como foco principal.

En el bloque actual se ajusto el saludo inicial del chat publico para evitar frases que den por hecho que el usuario ya cargo documentos. El objetivo es que la primera interaccion sea mas neutra y natural, manteniendo la posibilidad de hacer preguntas, pedir resumenes o comparar informacion cuando corresponda.

Tambien se ajusto el arranque de la API cloud para que no bloquee la experiencia inicial cargando embeddings si ya existe un indice publicado compatible. En ese caso, la API puede quedar lista usando el `chunk_cache` activo y responder antes, reduciendo el tiempo que el frontend permanece en `Preparando sistema`.
