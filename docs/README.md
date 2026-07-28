# Documentacion de AGROJ ESPECIALIZADO

Esta carpeta contiene la documentacion tecnica, operativa y de seguimiento del proyecto. La idea es que cualquier persona pueda entender el sistema, levantarlo, desplegarlo y continuar el trabajo sin depender de explicaciones externas.

## Lectura recomendada

Para una primera lectura, sigue este orden:

1. [project-status.md](project-status.md): estado actual, que esta hecho y que falta.
2. [architecture.md](architecture.md): arquitectura del sistema y decisiones tecnicas principales.
3. [cloud-run-jobs.md](cloud-run-jobs.md): como operar backend, frontend y reindexado en Google Cloud.
4. [cloud-contract.md](cloud-contract.md): contrato tecnico de documentos, indices, Firestore y Cloud Storage.
5. [glossary.md](glossary.md): terminos clave explicados en lenguaje sencillo.
6. [evidence-log.md](evidence-log.md): bitacora de errores, pruebas, decisiones y avances.
7. [memoria_tecnica_senadi.md](memoria_tecnica_senadi.md): memoria tecnica para registro formal del software.

## Mapa rapido

| Archivo | Para que sirve |
| --- | --- |
| `project-status.md` | Resume el estado real del proyecto, avances, riesgos y proximos pasos. |
| `architecture.md` | Explica la arquitectura RAG, frontend, backend, cloud, documentos e IA. |
| `cloud-contract.md` | Define como se organizan documentos, indices, manifiestos y estado en cloud. |
| `cloud-run-jobs.md` | Guia de build, deploy, reindexado, logs y monitoreo en Google Cloud. |
| `glossary.md` | Aclara conceptos como RAG, embeddings, corpus, Firestore y Cloud Run Jobs. |
| `evidence-log.md` | Registra eventos importantes del desarrollo, errores encontrados y correcciones. |
| `memoria_tecnica_senadi.md` | Describe tecnicamente el software para fines de proteccion y presentacion formal. |
| `work-summary-2026-05-11.md` | Resumen narrativo de una etapa especifica del trabajo. |

## Resumen tecnico corto

AGROJ ESPECIALIZADO es un sistema de consulta agricola basado en documentos PDF. Usa una arquitectura RAG:

```text
Pregunta del usuario
  -> busqueda en documentos indexados
  -> seleccion de fragmentos relevantes
  -> generacion de respuesta con Gemini
  -> respuesta clara en el chat
```

Componentes principales:

- `React + Vite`: interfaz web.
- `FastAPI`: backend y API.
- `LlamaIndex`: framework RAG.
- `sentence-transformers/all-MiniLM-L6-v2`: embeddings.
- `Gemini 2.5 Flash`: generacion de respuestas.
- `Cloud Storage`: documentos e indices.
- `Firestore`: metadatos y estado operativo.
- `Cloud Run`: backend y frontend.
- `Cloud Run Jobs`: reindexado pesado.

## Reglas de mantenimiento

Cuando se haga un cambio importante:

1. Actualizar `project-status.md`.
2. Actualizar `architecture.md` si cambia una decision tecnica.
3. Actualizar `cloud-run-jobs.md` si cambia algun comando o flujo de despliegue.
4. Agregar una entrada en `evidence-log.md` si hubo error, validacion, deploy, decision o prueba relevante.
5. Mantener `glossary.md` actualizado si aparece un termino nuevo importante.

## Criterio editorial

- Escribir para una persona que llega al proyecto por primera vez.
- Preferir explicaciones concretas sobre teoria larga.
- Mantener comandos listos para copiar y ejecutar.
- Separar estado vigente de historia pasada.
- No documentar secretos reales.
- No versionar indices, caches, builds ni archivos generados.

## Estado de documentacion

La documentacion actual ya cubre:

- arquitectura RAG del sistema
- operacion local
- despliegue en Google Cloud
- gestion documental
- subida masiva de documentos
- reindexado manual
- limpieza del repositorio
- memoria tecnica para SENADI

La bitacora historica se mantiene en `evidence-log.md`; no todo lo que aparece ahi representa el estado vigente, sino el camino recorrido.
