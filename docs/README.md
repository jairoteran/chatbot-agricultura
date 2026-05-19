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

- `project-status.md`: estado consolidado del panel admin, reindexado manual y proximos pasos de despliegue
- `architecture.md`: decisiones de arquitectura sobre panel administrativo, autenticacion Google y politica de reindexado manual
- `cloud-run-jobs.md`: operacion cloud actual, variables necesarias para admin y uso manual del reindexado
- `evidence-log.md`: errores importantes encontrados, decisiones tecnicas y correcciones aplicadas durante este bloque

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
