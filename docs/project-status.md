# Estado del proyecto

Este documento resume el estado vigente de AGROJ ESPECIALIZADO. La historia detallada queda en `evidence-log.md`.

## Resumen ejecutivo

AGROJ ESPECIALIZADO ya cuenta con:

- frontend publico en React + Vite
- backend en FastAPI
- arquitectura RAG con LlamaIndex
- embeddings con `sentence-transformers/all-MiniLM-L6-v2`
- generacion con Gemini
- panel de gestion documental en `/gestion`
- subida directa de PDFs pesados a Cloud Storage
- reindexado manual mediante Cloud Run Jobs
- estado y metadatos en Firestore
- despliegue preparado para Google Cloud
- documentacion tecnica reorganizada

## Estado vigente

| Area | Estado |
| --- | --- |
| Chat publico | Funcional, con tono conversacional unico. |
| Filtro de dominio | Activo para evitar preguntas fuera de agricultura. |
| RAG | Activo con recuperacion semantica y lexical. |
| Frontend movil | Redisenado con drawer lateral. |
| Gestion documental | Activa con Google Sign-In y cuentas autorizadas. |
| Subida de PDFs | Directa a Cloud Storage para evitar limite de Cloud Run. |
| Reindexado | Manual, ejecutado por Cloud Run Jobs. |
| Estado operativo | Persistido en Firestore. |
| Limpieza repo | Indices, caches, builds y PDFs de prueba quedan ignorados. |
| Marca | Producto nombrado como `AGROJ ESPECIALIZADO`. |

## Arquitectura actual

```text
Frontend Cloud Run
  -> Backend Cloud Run
  -> Cloud Storage: documentos e indices
  -> Firestore: metadatos y estado
  -> Cloud Run Jobs: reindexado
  -> Gemini: generacion
```

## Hecho recientemente

- Se adopto el nombre `AGROJ ESPECIALIZADO` en la interfaz y README.
- Se limpio el repo para no versionar `backend/storage/`.
- Se elimino configuracion heredada de Vercel.
- Se corrigio el `Dockerfile` para crear `storage/` vacio en runtime.
- Se agrego `.gcloudignore` para reducir el contexto de Cloud Build.
- Se reestructuro el README principal de GitHub.
- Se preparo documentacion mas clara en `/docs`.
- Se analizo un repositorio de 475 PDFs y se filtro una carpeta de 352 candidatos.
- Se ejecuto un reindexado cloud de gran volumen desde Cloud Run Jobs.

## Decisiones tecnicas importantes

### No entrenar modelo propio

El sistema no entrena un modelo desde cero. Usa modelos ya entrenados:

- Gemini para generar respuestas.
- `all-MiniLM-L6-v2` para embeddings.

Al subir documentos, lo que cambia es el indice, no los pesos de un modelo.

### Reindexado manual

El backend web no reindexa automaticamente. El reindexado se ejecuta manualmente desde:

- panel `/gestion`
- comando de Cloud Run Jobs

Esto evita timeouts y mantiene estable la API.

### Gestion documental sin roles rigidos

La fase actual usa cuentas autorizadas. No se presenta como una jerarquia cerrada de administrador.

Evolucion posible:

- colaborador
- revisor
- curador
- validador

### Respuestas con evidencia

El sistema debe preferir no responder antes que responder con fragmentos debiles o fuera del dominio agricola.

## Riesgos abiertos

- El reindexado con cientos de PDFs puede tardar varias horas.
- PDFs escaneados o con OCR pobre pueden aportar poco texto util.
- Si Gemini esta saturado, puede activarse fallback.
- Si el indice activo no queda publicado correctamente, la API puede iniciar sin recuperacion vectorial.
- La calidad de respuesta depende de la calidad documental cargada.
- Falta una suite de pruebas automatizadas para regresiones del RAG.

## Pendientes recomendados

1. Validar el reindexado masivo actual hasta que termine.
2. Revisar `/health` despues del job.
3. Probar preguntas sobre documentos nuevos.
4. Revisar documentos marcados como `review` antes de subirlos.
5. Crear capturas de evidencia del panel, Cloud Run, Cloud Storage y Firestore.
6. Agregar pruebas automaticas basicas para `/health`, `/chat` y validacion de dominio.
7. Revisar vulnerabilidades npm reportadas por `npm audit`.

## Comandos de validacion

Frontend:

```powershell
npm --prefix frontend run build
```

Backend health local:

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/health" |
  ConvertTo-Json -Depth 10
```

Backend health cloud:

```powershell
Invoke-RestMethod -Method Get `
  -Uri "https://tesis-producto-api-1025954944056.us-central1.run.app/health" |
  ConvertTo-Json -Depth 10
```

Jobs:

```powershell
gcloud run jobs executions list `
  --job tesis-producto-reindex `
  --region us-central1
```

## Como actualizar este archivo

Actualizar cuando:

- se cambie arquitectura
- se despliegue una version importante
- se modifique el flujo de documentos
- se agregue o quite una tecnologia relevante
- se cierre un riesgo
- aparezca un bloqueo nuevo

Mantener este archivo como resumen vigente. La bitacora detallada debe ir en `evidence-log.md`.
