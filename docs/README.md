# Documentacion del proyecto

Esta carpeta centraliza la documentacion operativa y de seguimiento del proyecto.

## Archivos principales

- [architecture.md](architecture.md): arquitectura objetivo en Google Cloud, responsabilidades y decisiones de alto nivel
- [cloud-contract.md](cloud-contract.md): contrato tecnico para documentos, indices, releases y estado cloud
- [cloud-run-jobs.md](cloud-run-jobs.md): contenedor, comandos y consideraciones para Cloud Run y Cloud Run Jobs
- [evidence-log.md](evidence-log.md): registro de capturas, errores, pruebas, interfaces y avances utiles para resultados y anexos
- [glossary.md](glossary.md): terminos tecnicos usados en el proyecto y su significado practico
- [project-status.md](project-status.md): estado actual, avances, pendientes y siguientes pasos
- [work-summary-2026-05-11.md](work-summary-2026-05-11.md): resumen narrativo del trabajo implementado, problemas resueltos y validaciones del bloque actual

## Bloque actual mas importante

En el estado actual del proyecto, los cambios mas relevantes quedaron documentados en:

- `project-status.md`: estado consolidado del panel de gestion documental, reindexado manual y proximos pasos de despliegue
- `architecture.md`: decisiones de arquitectura sobre gestion documental, autenticacion Google, cuentas autorizadas y politica de reindexado manual
- `architecture.md`: tambien documenta el modelo NLP real del sistema, el papel de Gemini y Hugging Face, el concepto de corpus y la evolucion recomendada de gobernanza documental
- `architecture.md`: documenta el enriquecimiento del corpus con `spaCy` y la decision de no incorporar `NLTK` mientras no aporte valor adicional claro
- `cloud-run-jobs.md`: operacion cloud actual, variables necesarias para acceso protegido y uso manual del reindexado
- `evidence-log.md`: errores importantes encontrados, decisiones tecnicas y correcciones aplicadas durante este bloque
- `evidence-log.md`: tambien registra cambios visibles de interfaz, tono conversacional y validaciones de build cuando afectan la experiencia del usuario
- `glossary.md`: incluye definiciones practicas de `RAG`, `corpus`, estados documentales, `embeddings`, `Gemini`, `Hugging Face`, `spaCy` y `NLTK`

## Regla de mantenimiento

Despues de cada bloque de trabajo importante, actualizar:

1. `project-status.md`
2. `architecture.md` si hubo cambios de direccion tecnica
3. `evidence-log.md` si hubo capturas, errores, pruebas o avances verificables

## Criterio de limpieza

- Documentar decisiones reales, no ideas sueltas que ya no apliquen
- Quitar informacion obsoleta cuando una estrategia deje de ser vigente
- Mantener pendientes concretos y accionables
- Evitar duplicar la misma explicacion en muchos archivos
