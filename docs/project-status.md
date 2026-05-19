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
- Se incorporo un panel administrativo protegido con Google Sign-In para gestionar acceso interno
- Se implemento carga manual, listado y eliminacion de PDFs desde el panel de administracion
- Se conecto el panel administrativo con sesiones validadas por backend y lista blanca de correos autorizados
- Se reemplazo el boton visual nativo de Google por una capa visual custom manteniendo el flujo real de autenticacion por debajo
- Se elimino el reindexado automatico en runtime y el flujo quedo completamente manual desde el panel de administracion
- Se agrego una accion manual `Reindexar ahora` en el panel de documentos y se bloquearon acciones concurrentes de subir, borrar y reindexar
- Se dejo configurado `backend/cloudrun.env.yaml` con `GOOGLE_AUTH_CLIENT_ID` y `ADMIN_EMAILS` para el despliegue cloud actual

## En progreso

- Transicion desde arquitectura local versionada en Git hacia almacenamiento administrado en Google Cloud
- Publicacion y validacion final del frontend y backend actualizados en cloud

## Pendiente inmediato

- Construir y desplegar backend y frontend con la version actual del panel admin
- Ejecutar validacion extremo a extremo del flujo admin: login, subida, reindex manual, consulta y borrado
- Verificar el comportamiento del job de reindexado cloud despues del redeploy

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

- Si se despliega backend sin secretos o variables admin correctas, el panel `/gestion` quedara inaccesible aunque el resto de la API siga viva
- El flujo real del panel admin todavia requiere validacion final en cloud con login Google y subida real de PDFs
- Pueden quedar blobs antiguos no PDF en el bucket de documentos si se usaron sincronizaciones anteriores sin filtrado
- Falta definir una estrategia limpia de versionado del indice publicado
- La validacion completa del servicio RAG depende de disponibilidad del modelo de embeddings durante arranque

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

En el bloque actual se completo el panel administrativo protegido bajo `/gestion`, con autenticacion por Google, sesiones administradas por backend, carga y borrado manual de documentos, y reindexado manual disparado desde la UI. Tambien se decidio quitar el reindexado automatico en runtime para que el backend web no reconstruya el indice por si solo cuando detecta cambios documentales.
